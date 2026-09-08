import logging
import traceback
from datetime import datetime
from typing import Any, Self, TYPE_CHECKING
from uuid import uuid4

from flask import current_app, url_for

from .exceptions import NotFoundException, DatabaseException, ErrorException
from .parser import parse_minifig
from .bricklink import BrickLink
from .rebrickable_minifigure import RebrickableMinifigure
from .set_owner_list import BrickSetOwnerList
from .set_purchase_location_list import BrickSetPurchaseLocationList
from .set_storage_list import BrickSetStorageList
from .set_tag_list import BrickSetTagList
from .sql import BrickSQL

if TYPE_CHECKING:
    from .socket import BrickSocket

logger = logging.getLogger(__name__)


# Individual minifigure (not associated with a set)
class IndividualMinifigure(RebrickableMinifigure):
    # Queries
    select_query: str = 'individual_minifigure/select/by_id'
    insert_query: str = 'individual_minifigure/insert'

    # Delete an individual minifigure
    def delete(self, /) -> None:
        BrickSQL().executescript(
            'individual_minifigure/delete',
            id=self.fields.id
        )

    # Import an individual minifigure into the database
    def download(self, socket: 'BrickSocket', data: dict[str, Any], /) -> bool:
        # Load the minifigure
        if not self.load(socket, data, from_download=True):
            return False

        try:
            # Insert into the database
            socket.auto_progress(
                message='Minifigure {figure}: inserting into database'.format(
                    figure=self.fields.figure
                ),
                increment_total=True,
            )

            # Generate an UUID for self
            self.fields.id = str(uuid4())

            # Save the storage
            storage = BrickSetStorageList.get(
                data.get('storage', ''),
                allow_none=True
            )
            self.fields.storage = storage.fields.id if storage else None

            # Save the purchase location
            purchase_location = BrickSetPurchaseLocationList.get(
                data.get('purchase_location', ''),
                allow_none=True
            )
            self.fields.purchase_location = purchase_location.fields.id if purchase_location else None

            # Save purchase date and price
            purchase_date = data.get('purchase_date', None)
            if purchase_date == '':
                purchase_date = None
            if purchase_date is not None:
                try:
                    purchase_date = datetime.strptime(purchase_date, '%Y/%m/%d').timestamp()
                except Exception:
                    purchase_date = None
            self.fields.purchase_date = purchase_date

            purchase_price = data.get('purchase_price', None)
            if purchase_price == '':
                purchase_price = None
            if purchase_price is not None:
                try:
                    purchase_price = float(purchase_price)
                except Exception:
                    purchase_price = None
            self.fields.purchase_price = purchase_price

            # Save quantity and description
            self.fields.quantity = int(data.get('quantity', 1))
            self.fields.description = data.get('description', '')

            # IMPORTANT: Insert rebrickable minifigure FIRST
            # bricktracker_individual_minifigures has FK to rebrickable_minifigures
            self.insert_rebrickable_loose()

            # Now insert into bricktracker_individual_minifigures
            # Use no_defer=True to ensure the insert happens before we insert parts
            # (parts have a foreign key constraint on this id)
            self.insert(commit=False, no_defer=True)

            # Save the owners
            owners: list[str] = list(data.get('owners', []))
            for id in owners:
                owner = BrickSetOwnerList.get(id)
                owner.update_individual_minifigure_state(self, state=True)

            # Save the tags
            tags: list[str] = list(data.get('tags', []))
            for id in tags:
                tag = BrickSetTagList.get(id)
                tag.update_individual_minifigure_state(self, state=True)

            # Load the parts (elements) for this minifigure
            if not self.download_parts(socket):
                return False

            # Commit the transaction to the database
            socket.auto_progress(
                message='Minifigure {figure}: writing to the database'.format(
                    figure=self.fields.figure
                ),
                increment_total=True,
            )

            BrickSQL().commit()

            # Info
            logger.info('Minifigure {figure}: imported (id: {id})'.format(
                figure=self.fields.figure,
                id=self.fields.id,
            ))

            # Complete
            socket.complete(
                message='Minifigure {figure}: imported (<a href="{url}">Go to the minifigure</a>)'.format(
                    figure=self.fields.figure,
                    url=self.url()
                ),
                download=True
            )

        except Exception as e:
            socket.fail(
                message='Error while importing minifigure {figure}: {error}'.format(
                    figure=self.fields.figure,
                    error=e,
                )
            )

            logger.debug(traceback.format_exc())

            return False

        return True

    # Download parts (elements) for this individual minifigure
    def download_parts(self, socket: 'BrickSocket', /) -> bool:
        try:
            socket.auto_progress(
                message='Minifigure {figure}: loading parts from the BrickLink catalog'.format(  # noqa: E501
                    figure=self.fields.figure
                ),
                increment_total=True,
            )

            from .part import BrickPart

            parts = BrickLink[BrickPart](
                'get_minifig_elements',
                self.fields.figure,
                BrickPart,
                socket=socket,
            ).list()

            socket.auto_progress(
                message='Minifigure {figure}: saving parts to database'.format(
                    figure=self.fields.figure
                ),
            )

            for part in parts:
                record = part.sql_parameters()

                # Справочная запись о детали
                BrickSQL().execute(
                    'rebrickable/part/insert',
                    parameters=record,
                    commit=False,
                )

                if not current_app.config['USE_REMOTE_IMAGES']:
                    from .rebrickable_image import RebrickableImage
                    from .set import BrickSet

                    try:
                        RebrickableImage(
                            BrickSet(),
                            minifigure=self,
                            part=part,
                        ).download()
                    except Exception as e:
                        logger.warning(
                            'Could not download image for part {part}: {error}'.format(  # noqa: E501
                                part=record['part'],
                                error=e,
                            )
                        )

                BrickSQL().execute(
                    'individual_minifigure/part/insert',
                    parameters={
                        'id': self.fields.id,
                        'part': record['part'],
                        'color': record['color'],
                        'spare': record['spare'],
                        'quantity': record['quantity'],
                        'element': record['element'],
                        'rebrickable_inventory': record['rebrickable_inventory'],
                        'counterpart': record['counterpart'],
                        'alternate': record['alternate'],
                        'match_id': record['match_id'],
                    },
                    commit=False,
                )

            logger.debug('Inserted {count} parts for minifigure {figure}'.format(  # noqa: E501
                count=len(parts),
                figure=self.fields.figure,
            ))

            return True

        except Exception as e:
            socket.fail(
                message='Error loading parts for minifigure {figure}: {error}'.format(
                    figure=self.fields.figure,
                    error=e,
                )
            )
            logger.debug(traceback.format_exc())
            return False

    # Insert the individual minifigure from Rebrickable
    def insert_rebrickable_loose(self, /) -> None:
        # Insert the Rebrickable minifigure to the database
        # Note: We override the parent's insert_rebrickable since we don't have a brickset
        from .rebrickable_image import RebrickableImage

        # Explicitly build parameters for rebrickable_minifigures insert
        params = {
            'figure': self.fields.figure,
            'number': self.fields.number,
            'name': self.fields.name,
            'image': self.fields.image,
            'number_of_parts': self.fields.number_of_parts,
        }

        BrickSQL().execute(
            RebrickableMinifigure.insert_query,
            parameters=params,
            commit=False,
        )

        # Download image locally if not using remote images
        if not current_app.config['USE_REMOTE_IMAGES']:
            # Create a dummy BrickSet for RebrickableImage
            # RebrickableImage checks minifigure first before set, so this works
            from .set import BrickSet
            try:
                RebrickableImage(
                    BrickSet(),  # Dummy set - not used since minifigure takes priority
                    minifigure=self,
                ).download()
                logger.debug('Downloaded image for individual minifigure {figure}'.format(
                    figure=self.fields.figure
                ))
            except Exception as e:
                logger.warning(
                    'Could not download image for individual minifigure {figure}: {error}'.format(
                        figure=self.fields.figure,
                        error=e
                    )
                )

    # Load the minifigure from Rebrickable
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
            # Check if individual minifigures are disabled
            from flask import current_app
            if current_app.config.get('DISABLE_INDIVIDUAL_MINIFIGURES', False):
                raise ErrorException(
                    'Individual minifigures system is disabled. '
                    'Only set-based minifigures can be added.'
                )

            socket.auto_progress(message='Parsing minifigure number')
            figure = parse_minifig(str(data['figure']))

            socket.auto_progress(
                message='Minifigure {figure}: loading from the BrickLink catalog'.format(  # noqa: E501
                    figure=figure,
                ),
            )

            logger.debug('BrickLink catalog get_minifigure("{figure}")'.format(
                figure=figure,
            ))

            # Каталог отдаёт и саму фигурку, и её состав, поэтому
            # прежняя связка из двух запросов не нужна
            BrickLink[IndividualMinifigure](
                'get_minifigure',
                figure,
                IndividualMinifigure,
                instance=self,
            ).get()

            # Как и у набора: картинка нужна до отправки short(), в том
            # числе на пути импорта, иначе оттуда уйдёт удалённый адрес
            if not current_app.config['USE_REMOTE_IMAGES'] and self.fields.image:  # noqa: E501
                from .rebrickable_image import RebrickableImage
                from .set import BrickSet
                try:
                    RebrickableImage(
                        BrickSet(),
                        minifigure=self,
                    ).download()
                    logger.debug('Downloaded preview image for minifigure {figure}'.format(
                        figure=self.fields.figure
                    ))
                except Exception as e:
                    logger.warning(
                        'Could not download preview image for minifigure {figure}: {error}'.format(
                            figure=self.fields.figure,
                            error=e
                        )
                    )

            socket.emit('MINIFIGURE_LOADED', self.short(
                from_download=from_download
            ))

            if not from_download:
                socket.complete(
                    message='Minifigure {figure}: loaded from the BrickLink catalog'.format(  # noqa: E501
                        figure=self.fields.figure
                    )
                )

            return True

        except Exception as e:
            # Check if this is the "disabled" error - if so, show cleaner message
            error_msg = str(e)
            if 'Individual minifigures system is disabled' in error_msg:
                socket.fail(message=error_msg)
            else:
                socket.fail(
                    message='Could not load the minifigure from the BrickLink catalog: {error}. Data: {data}'.format(  # noqa: E501
                        error=error_msg,
                        data=data,
                    )
                )

            if not isinstance(e, (NotFoundException, ErrorException)):
                logger.debug(traceback.format_exc())

        return False

    # Return a short form of the minifigure
    def short(self, /, *, from_download: bool = False) -> dict[str, Any]:
        from .rebrickable_image import RebrickableImage
        from .set import BrickSet

        # Локальный адрес — только если картинка действительно скачалась,
        # иначе предпросмотр покажет битую ссылку вместо рабочей удалённой
        if (
            not current_app.config['USE_REMOTE_IMAGES']
            and self.fields.image
            and not RebrickableImage(
                BrickSet(),
                minifigure=self,
            ).cached()
        ):
            image = self.fields.image
        else:
            image = self.url_for_image()

        return {
            'download': from_download,
            'image': image,
            'name': self.fields.name,
            'figure': self.fields.figure,
        }

    # Select an individual minifigure by ID
    def select_by_id(self, id: str, /) -> Self:
        # Save the ID parameter
        self.fields.id = id

        # Import status list here to get metadata columns
        from .set_status_list import BrickSetStatusList

        # Pass metadata columns to the query (using set tables which now handle all entities)
        context = {
            'owners': BrickSetOwnerList.as_columns() if BrickSetOwnerList.list() else '',
            'statuses': BrickSetStatusList.as_columns(all=True) if BrickSetStatusList.list(all=True) else '',
            'tags': BrickSetTagList.as_columns() if BrickSetTagList.list() else '',
        }

        if not self.select(**context):
            raise NotFoundException(
                'Individual minifigure with ID {id} was not found in the database'.format(
                    id=id,
                ),
            )

        return self

    # URL to this individual minifigure instance
    def url(self, /) -> str:
        return url_for('individual_minifigure.details', id=self.fields.id)

    # String representation for debugging
    def __repr__(self, /) -> str:
        figure = getattr(self.fields, 'figure', 'unknown')
        name = getattr(self.fields, 'name', 'Unknown')
        qty = getattr(self.fields, 'quantity', 0)
        return f'<IndividualMinifigure {figure} "{name}" qty:{qty}>'

    # URL for updating quantity
    def url_for_quantity(self, /) -> str:
        return url_for('individual_minifigure.update_quantity', id=self.fields.id)

    # URL for updating description
    def url_for_description(self, /) -> str:
        return url_for('individual_minifigure.update_description', id=self.fields.id)

    # Parts
    def generic_parts(self, /):
        from .part_list import BrickPartList
        return BrickPartList().from_individual_minifigure(self)

    # Override from_rebrickable to handle minifigure data
    @staticmethod
    def from_rebrickable(data: dict[str, Any], /, **_) -> dict[str, Any]:
        # Extracting number
        number = int(str(data['set_num'])[5:])

        return {
            'figure': str(data['set_num']),
            'number': int(number),
            'name': str(data['set_name']),
            'image': str(data['set_img_url']) if data.get('set_img_url') else None,
            'number_of_parts': int(data.get('num_parts', 0)),
        }
