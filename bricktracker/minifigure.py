import logging
import traceback
from typing import Self, TYPE_CHECKING

from .exceptions import ErrorException, NotFoundException
from .part_list import BrickPartList
from .sql import BrickSQL
from .rebrickable_minifigure import RebrickableMinifigure
if TYPE_CHECKING:
    from .set import BrickSet
    from .socket import BrickSocket

logger = logging.getLogger(__name__)


# Lego minifigure
class BrickMinifigure(RebrickableMinifigure):
    # Queries
    insert_query: str = 'minifigure/insert'
    generic_query: str = 'minifigure/select/generic'
    select_query: str = 'minifigure/select/specific'

    # Import a minifigure into the database
    def download(self, socket: 'BrickSocket', refresh: bool = False) -> bool:
        if self.brickset is None:
            raise ErrorException('Importing a minifigure outside of a set is not supported')  # noqa: E501

        try:
            # Insert into the database
            socket.auto_progress(
                message='Set {set}: inserting minifigure {figure} into database'.format(  # noqa: E501
                    set=self.brickset.fields.set,
                    figure=self.fields.figure
                )
            )

            # Load the inventory (needed to count parts for rebrickable record)
            if not BrickPartList.download(
                socket,
                self.brickset,
                minifigure=self,
                refresh=refresh
            ):
                return False

            # Insert the rebrickable minifigure into database first (parent record)
            # This must happen before inserting into bricktracker_minifigures due to FK constraint
            self.insert_rebrickable()

            if refresh:
                params = self.sql_parameters()

                # Отмечаем, что фигурка встретилась: всё неотмеченное
                # будет удалено после обхода
                BrickSQL().execute(
                    'minifigure/track_refresh_minifigure',
                    parameters=params,
                    defer=False,
                )

                # Сначала пробуем обновить: так сохраняются отметки
                # missing и damaged. Раньше при обновлении строки фигурок
                # не трогались вовсе, и расхождение с каталогом было не
                # починить ничем, кроме переустановки набора.
                rows, _ = BrickSQL().execute(
                    'minifigure/update_on_refresh',
                    parameters=params,
                    defer=False,
                )

                # Не обновилось — значит фигурки ещё не было
                if rows == 0:
                    self.insert(commit=False)
            else:
                # Insert into bricktracker_minifigures database (child record)
                self.insert(commit=False)

        except Exception as e:
            socket.fail(
                message='Error while importing minifigure {figure} from {set}: {error}'.format(  # noqa: E501
                    figure=self.fields.figure,
                    set=self.brickset.fields.set,
                    error=e,
                )
            )

            logger.debug(traceback.format_exc())

            return False

        return True

    # Parts
    def generic_parts(self, /) -> BrickPartList:
        return BrickPartList().from_minifigure(self)

    # Parts
    def parts(self, /) -> BrickPartList:
        if self.brickset is None:
            raise ErrorException('Part list for minifigure {figure} requires a brickset'.format(  # noqa: E501
                figure=self.fields.figure,
            ))

        return BrickPartList().list_specific(self.brickset, minifigure=self)

    # Select a generic minifigure
    def select_generic(self, figure: str, /) -> Self:
        # Save the parameters to the fields
        self.fields.figure = figure

        if not self.select(override_query=self.generic_query):
            raise NotFoundException(
                'Minifigure with figure {figure} was not found in the database'.format(  # noqa: E501
                    figure=self.fields.figure,
                ),
            )

        return self

    # Select a specific minifigure (with a set and a figure)
    def select_specific(self, brickset: 'BrickSet', figure: str, /) -> Self:
        # Save the parameters to the fields
        self.brickset = brickset
        self.fields.figure = figure

        if not self.select():
            raise NotFoundException(
                'Minifigure with figure {figure} from set {set} was not found in the database'.format(  # noqa: E501
                    figure=self.fields.figure,
                    set=self.brickset.fields.set,
                ),
            )

        return self
