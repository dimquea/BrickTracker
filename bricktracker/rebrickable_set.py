import logging
from sqlite3 import Row
import traceback
from typing import Any, Self, TYPE_CHECKING

from flask import current_app, url_for

from .bricklink import BrickLink
from .bricklink_catalog import image_url, ITEM_TYPE_SET
from .exceptions import ErrorException, NotFoundException
from .instructions import BrickInstructions
from .parser import parse_set
from .rebrickable_image import RebrickableImage
from .record import BrickRecord
from .theme_list import BrickThemeList
if TYPE_CHECKING:
    from .socket import BrickSocket
    from .theme import BrickTheme

logger = logging.getLogger(__name__)


# A set from Rebrickable
class RebrickableSet(BrickRecord):
    theme: 'BrickTheme'
    instructions: list[BrickInstructions]

    # Flags
    resolve_instructions: bool = True

    # Queries
    select_query: str = 'rebrickable/set/select'
    insert_query: str = 'rebrickable/set/insert'

    def __init__(
        self,
        /,
        *,
        record: Row | dict[str, Any] | None = None
    ):
        super().__init__()

        # Placeholders
        self.instructions = []

        # Ingest the record if it has one
        if record is not None:
            self.ingest(record)

    # Insert the set from Rebrickable
    def insert_rebrickable(self, /) -> None:
        # Insert the Rebrickable set to the database
        self.insert(
            commit=False,
            no_defer=True,
            override_query=RebrickableSet.insert_query
        )

        if not current_app.config['USE_REMOTE_IMAGES']:
            RebrickableImage(self).download()

    # Ingest a set
    def ingest(self, record: Row | dict[str, Any], /):
        super().ingest(record)

        # Resolve theme
        if not hasattr(self.fields, 'theme_id'):
            self.fields.theme_id = 0

        self.theme = BrickThemeList().get(self.fields.theme_id)

        # Resolve instructions
        if self.resolve_instructions:
            # Not idead, avoiding cyclic import
            from .instructions_list import BrickInstructionsList

            if self.fields.set is not None:
                self.instructions = BrickInstructionsList().get(
                    self.fields.set
                )

    # Load the set from Rebrickable
    def load(
        self,
        socket: 'BrickSocket',
        data: dict[str, Any],
        /,
        *,
        from_download=False,
    ) -> bool:
        # Reset the progress
        socket.progress_count = 0
        socket.progress_total = 2

        try:
            socket.auto_progress(message='Parsing set number')
            set = parse_set(str(data['set']))

            # Check if this is actually a minifigure (starts with fig-)
            # If so, redirect to the minifigure handler
            if set.startswith('fig-'):
                from .individual_minifigure import IndividualMinifigure
                # Transform data: minifigure handler expects 'figure' key instead of 'set'
                minifig_data = data.copy()
                minifig_data['figure'] = minifig_data.pop('set')
                if from_download:
                    return IndividualMinifigure().download(socket, minifig_data)
                else:
                    return IndividualMinifigure().load(socket, minifig_data)

            socket.auto_progress(
                message='Set {set}: loading from the BrickLink catalog'.format(
                    set=set,
                ),
            )

            logger.debug('BrickLink catalog get_set("{set}")'.format(
                set=set,
            ))

            BrickLink[RebrickableSet](
                'get_set',
                set,
                RebrickableSet,
                instance=self,
            ).get()

            socket.emit('SET_LOADED', self.short(
                from_download=from_download
            ))

            if not from_download:
                socket.complete(
                    message='Set {set}: loaded from Rebrickable'.format(
                        set=self.fields.set
                    )
                )

            return True

        except Exception as e:
            socket.fail(
                message='Could not load the set from Rebrickable: {error}. Data: {data}'.format(  # noqa: E501
                    error=str(e),
                    data=data,
                )
            )

            if not isinstance(e, (NotFoundException, ErrorException)):
                logger.debug(traceback.format_exc())

        return False

    # Select a specific set (with a set)
    def select_specific(self, set: str, /) -> Self:
        # Save the parameters to the fields
        self.fields.set = set

        # Load from database
        if not self.select():
            raise NotFoundException(
                'Set with set {set} was not found in the database'.format(
                    set=self.fields.set,
                ),
            )

        return self

    # Return a short form of the Rebrickable set
    def short(self, /, *, from_download: bool = False) -> dict[str, Any]:
        # Use nil image URL if set image is null
        image_url = self.fields.image
        if image_url is None:
            # Return path to nil.png from parts folder
            image_url = RebrickableImage.static_url(
                RebrickableImage.nil_name(),
                'PARTS_FOLDER'
            )

        return {
            'download': from_download,
            'image': image_url,
            'name': self.fields.name,
            'set': self.fields.set,
        }

    # Compute the url for the set image
    def url_for_image(self, /) -> str:
        if not current_app.config['USE_REMOTE_IMAGES']:
            return RebrickableImage.static_url(
                self.fields.set,
                'SETS_FOLDER'
            )
        else:
            return self.fields.image

    # Compute the url for the rebrickable page
    def url_for_rebrickable(self, /) -> str:
        if current_app.config['REBRICKABLE_LINKS']:
            return self.fields.url

        return ''

    # Compute the url for the bricklink page
    def url_for_bricklink(self, /) -> str:
        if current_app.config['BRICKLINK_LINKS']:
            return current_app.config['BRICKLINK_LINK_SET_PATTERN'].format(
                set_num=self.fields.set
            )

        return ''

    # Compute the url for the refresh button
    def url_for_refresh(self, /) -> str:
        return url_for('set.refresh', set=self.fields.set)

    # Normalize from the BrickLink catalog
    @staticmethod
    def from_bricklink(data: dict[str, Any], /, **_) -> dict[str, Any]:
        # У BrickLink идентификатор набора той же формы, что был у
        # Rebrickable: номер, дефис, версия.
        number, _, version = str(data['ITEMID']).partition('-')

        return {
            'set': str(data['ITEMID']),
            'number': str(number),
            'version': int(version) if version else 1,
            'name': str(data['ITEMNAME']),
            # У части позиций каталога года нет
            'year': int(data['ITEMYEAR']) if data.get('ITEMYEAR') else 0,
            'theme_id': int(data['CATEGORY']),
            'number_of_parts': int(data['NUMBER_OF_PARTS']),
            'image': image_url(ITEM_TYPE_SET, str(data['ITEMID'])),
            'url': current_app.config['BRICKLINK_LINK_SET_PATTERN'].format(
                set_num=str(data['ITEMID']),
            ),
            # В выгрузке даты изменения нет
            'last_modified': '',
        }

    # Normalize from Rebrickable
    @staticmethod
    def from_rebrickable(data: dict[str, Any], /, **_) -> dict[str, Any]:
        # Extracting version and number
        # Note: number can be alphanumeric (e.g., "McDR6US", "COMCON035")
        number, _, version = str(data['set_num']).partition('-')

        return {
            'set': str(data['set_num']),
            'number': str(number),  # Keep as string to support alphanumeric sets
            'version': int(version),
            'name': str(data['name']),
            'year': int(data['year']),
            'theme_id': int(data['theme_id']),
            'number_of_parts': int(data['num_parts']),
            'image': str(data['set_img_url']) if data['set_img_url'] is not None else None,
            'url': str(data['set_url']),
            'last_modified': str(data['last_modified_dt']),
        }
