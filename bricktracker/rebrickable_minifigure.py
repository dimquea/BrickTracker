from sqlite3 import Row
from typing import Any, TYPE_CHECKING

from flask import current_app, url_for

from .bricklink_catalog import image_url, ITEM_TYPE_MINIFIGURE
from .custom_catalog import custom_catalog_url
from .exceptions import ErrorException
from .rebrickable_image import RebrickableImage
from .record import BrickRecord
if TYPE_CHECKING:
    from .set import BrickSet


# A minifigure from Rebrickable
class RebrickableMinifigure(BrickRecord):
    brickset: 'BrickSet | None'

    select_query: str = 'rebrickable/minifigure/select'
    insert_query: str = 'rebrickable/minifigure/insert'

    def __init__(
        self,
        /,
        *,
        brickset: 'BrickSet | None' = None,
        record: Row | dict[str, Any] | None = None
    ):
        super().__init__()

        self.brickset = brickset

        if record is not None:
            self.ingest(record)

    # Insert the minifigure from Rebrickable
    def insert_rebrickable(self, /) -> None:
        if self.brickset is None:
            raise ErrorException('Importing a minifigure outside of a set is not supported')  # noqa: E501

        # Insert the Rebrickable minifigure to the database
        self.insert(
            commit=False,
            no_defer=True,
            override_query=RebrickableMinifigure.insert_query
        )

        if not current_app.config['USE_REMOTE_IMAGES']:
            RebrickableImage(
                self.brickset,
                minifigure=self,
            ).download()

    # Return a dict with common SQL parameters for a minifigure
    def sql_parameters(self, /) -> dict[str, Any]:
        parameters = super().sql_parameters()

        # Supplement from the brickset
        if self.brickset is not None and 'id' not in parameters:
            parameters['id'] = self.brickset.fields.id

        return parameters

    def url(self, /) -> str:
        return url_for(
            'minifigure.details',
            figure=self.fields.figure,
        )

    # Compute the url for minifigure image
    def url_for_image(self, /) -> str:
        if not current_app.config['USE_REMOTE_IMAGES']:
            if self.fields.image is None:
                file = RebrickableImage.nil_minifigure_name()
            else:
                file = self.fields.figure

            return RebrickableImage.static_url(file, 'MINIFIGURES_FOLDER')
        else:
            if self.fields.image is None:
                return current_app.config['REBRICKABLE_IMAGE_NIL_MINIFIGURE']
            else:
                return self.fields.image

    # Compute the url for the custom catalog page
    def url_for_custom_catalog(self, /) -> str:
        return custom_catalog_url(
            'CUSTOM_CATALOG_LINK_MINIFIGURE_PATTERN',
            figure=self.fields.figure,
        )

    # Compute the url for the bricklink page
    def url_for_bricklink(self, /) -> str:
        if current_app.config['BRICKLINK_LINKS']:
            return current_app.config['BRICKLINK_LINK_MINIFIGURE_PATTERN'].format(  # noqa: E501
                figure=self.fields.figure,
            )

        return ''

    # Normalize from the BrickLink catalog
    @staticmethod
    def from_bricklink(data: dict[str, Any], /, **_) -> dict[str, Any]:
        figure = str(data['ITEMID'])

        return {
            'figure': figure,
            # У Rebrickable здесь лежала числовая часть fig-######.
            # Идентификаторы BrickLink буквенно-цифровые (oct054, sw1029),
            # поэтому колонка хранит их целиком.
            'number': figure,
            'name': str(data.get('ITEMNAME', figure)),
            'quantity': int(data.get('QTY', 1)),
            # Секция Alternate: взаимозаменяемые позиции с общим match_id
            'alternate': data.get('ALTERNATE', 'N') == 'Y',
            'match_id': int(data.get('MATCHID', 0) or 0),
            'image': image_url(ITEM_TYPE_MINIFIGURE, figure),
            # Внутри набора состав фигурки не читается, там его считает
            # загрузчик деталей
            'number_of_parts': int(data.get('NUMBER_OF_PARTS', 0) or 0),
        }

    # Normalize from Rebrickable
    @staticmethod
    def from_rebrickable(data: dict[str, Any], /, **_) -> dict[str, Any]:
        number = int(str(data['set_num'])[5:])

        return {
            'figure': str(data['set_num']),
            'number': int(number),
            'name': str(data['set_name']),
            'quantity': int(data['quantity']),
            'image': str(data['set_img_url']) if data['set_img_url'] else None,
        }
