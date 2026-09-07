import os
from sqlite3 import Row
from typing import Any, TYPE_CHECKING
from urllib.parse import urlparse

from flask import current_app, url_for

from .bricklink_catalog import image_name, image_url, ITEM_TYPE_PART
from .custom_catalog import custom_catalog_url
from .exceptions import ErrorException
from .rebrickable_image import RebrickableImage
from .record import BrickRecord
if TYPE_CHECKING:
    from .minifigure import BrickMinifigure
    from .set import BrickSet
    from .socket import BrickSocket


# A part from Rebrickable
class RebrickablePart(BrickRecord):
    socket: 'BrickSocket'
    brickset: 'BrickSet | None'
    minifigure: 'BrickMinifigure | None'

    # Queries
    select_query: str = 'rebrickable/part/select'
    insert_query: str = 'rebrickable/part/insert'

    def __init__(
        self,
        /,
        *,
        brickset: 'BrickSet | None' = None,
        minifigure: 'BrickMinifigure | None' = None,
        record: Row | dict[str, Any] | None = None
    ):
        super().__init__()

        # Save the brickset
        self.brickset = brickset

        # Save the minifigure
        self.minifigure = minifigure

        # Ingest the record if it has one
        if record is not None:
            self.ingest(record)

    # Insert the part from Rebrickable
    def insert_rebrickable(self, /) -> None:
        if self.brickset is None:
            raise ErrorException('Importing a part outside of a set is not supported')  # noqa: E501

        # Insert the Rebrickable part to the database
        self.insert(
            commit=False,
            no_defer=True,
            override_query=RebrickablePart.insert_query
        )

        if not current_app.config['USE_REMOTE_IMAGES']:
            RebrickableImage(
                self.brickset,
                minifigure=self.minifigure,
                part=self,
            ).download()

    # Return a dict with common SQL parameters for a part
    def sql_parameters(self, /) -> dict[str, Any]:
        parameters = super().sql_parameters()

        # Individual minifigure id takes precedence
        if hasattr(self, 'individual_minifigure') and self.individual_minifigure is not None:
            parameters['id'] = self.individual_minifigure.fields.id
        # Set id
        elif self.brickset is not None:
            parameters['id'] = self.brickset.fields.id

        # Use the minifigure number if present,
        if self.minifigure is not None:
            parameters['figure'] = self.minifigure.fields.figure
        else:
            parameters['figure'] = None

        return parameters

    # Self url
    def url(self, /) -> str:
        return url_for(
            'part.details',
            part=self.fields.part,
            color=self.fields.color,
        )

    # Compute the url for the bricklink page
    def url_for_bricklink(self, /) -> str:
        if current_app.config['BRICKLINK_LINKS']:
            try:
                # Use BrickLink part number if available and not None/empty, otherwise fall back to Rebrickable part
                bricklink_part = getattr(self.fields, 'bricklink_part_num', None)
                part_param = bricklink_part if bricklink_part else self.fields.part

                # Use BrickLink color ID if available and not None, otherwise fall back to Rebrickable color
                bricklink_color = getattr(self.fields, 'bricklink_color_id', None)
                color_param = bricklink_color if bricklink_color is not None else self.fields.color
                # print(f'BrickLink URL parameters: part={part_param}, color={color_param}')  # Debugging line, can be removed later
                return current_app.config['BRICKLINK_LINK_PART_PATTERN'].format(  # noqa: E501
                    part=part_param,
                    color=color_param,
                )
            except Exception:
                pass

        return ''

    # Compute the url for the part image
    def url_for_image(self, /) -> str:
        if not current_app.config['USE_REMOTE_IMAGES']:
            if self.fields.image is None:
                file = RebrickableImage.nil_name()
            else:
                file = self.fields.image_id

            return RebrickableImage.static_url(file, 'PARTS_FOLDER')
        else:
            if self.fields.image is None:
                return current_app.config['REBRICKABLE_IMAGE_NIL']
            else:
                return self.fields.image

    # Compute the url for the original of the printed part
    def url_for_print(self, /) -> str:
        if self.fields.print is not None:
            return url_for(
                'part.details',
                part=self.fields.print,
                color=self.fields.color,
            )
        else:
            return ''

    # Compute the url for the custom catalog page
    def url_for_custom_catalog(self, /) -> str:
        return custom_catalog_url(
            'CUSTOM_CATALOG_LINK_PART_PATTERN',
            part=self.fields.part,
            color=self.fields.color,
        )

    # Normalize from the BrickLink catalog
    @staticmethod
    def from_bricklink(
        data: dict[str, Any],
        /,
        *,
        brickset: 'BrickSet | None' = None,
        minifigure: 'BrickMinifigure | None' = None,
        **_,
    ) -> dict[str, Any]:
        reference = data.get('reference', {})
        color = data.get('color_reference', {})

        part = str(data['item'])
        color_id = int(data['color'])

        return {
            'id': None,
            'figure': None,
            'part': part,
            'color': color_id,
            # Секция Extra: запасные детали
            'spare': data['extra'],
            'quantity': int(data['quantity']),
            # Секция Counterpart: деталь, полученная из другой, например
            # применением наклейки. Не отдельная физическая деталь.
            'counterpart': data['counterpart'],
            # Секция Alternate: взаимозаменяемые позиции, сгруппированные
            # общим match_id
            'alternate': data['alternate'],
            'match_id': int(data['match_id']),
            # Своего идентификатора строки инвентаря у BrickLink нет
            'rebrickable_inventory': 0,
            # Идентификаторы элементов LEGO в выгрузке отсутствуют
            'element': None,
            'color_id': color_id,
            'color_name': color.get('COLORNAME', ''),
            'color_rgb': color.get('COLORRGB', ''),
            'color_transparent': color.get('COLORTYPE', '') == 'Transparent',
            # Каталог теперь и есть BrickLink, так что переводить нечего
            'bricklink_color_id': color_id,
            'bricklink_color_name': color.get('COLORNAME', ''),
            'bricklink_part_num': part,
            'name': reference.get('ITEMNAME', part),
            'category': int(reference['CATEGORY']) if reference.get('CATEGORY') else None,  # noqa: E501
            'image': image_url(ITEM_TYPE_PART, part, color=color_id),
            'image_id': image_name(ITEM_TYPE_PART, part, color=color_id),
            'url': current_app.config['BRICKLINK_LINK_PART_PATTERN'].format(
                part=part,
                color=color_id,
            ),
            # Ссылки на базовую деталь для декорированных вариантов в
            # выгрузке нет
            'print': None,
        }

    # Normalize from Rebrickable
    @staticmethod
    def from_rebrickable(
        data: dict[str, Any],
        /,
        *,
        brickset: 'BrickSet | None' = None,
        minifigure: 'BrickMinifigure | None' = None,
        **_,
    ) -> dict[str, Any]:
        record = {
            'id': None,
            'figure': None,
            'part': data['part']['part_num'],
            'color': data['color']['id'],
            'spare': data['is_spare'],
            'quantity': data['quantity'],
            'rebrickable_inventory': data['id'],
            'element': data['element_id'],
            'color_id': data['color']['id'],
            'color_name': data['color']['name'],
            'color_rgb': data['color']['rgb'],
            'color_transparent': data['color']['is_trans'],
            'bricklink_color_id': None,
            'bricklink_color_name': None,
            'bricklink_part_num': None,
            'name': data['part']['name'],
            'category': data['part']['part_cat_id'],
            'image': data['part']['part_img_url'],
            'image_id': None,
            'url': data['part']['part_url'],
            'print': data['part']['print_of']
        }

        # Extract BrickLink color info if available in external_ids
        if 'color' in data and 'external_ids' in data['color']:
            external_ids = data['color']['external_ids']
            if 'BrickLink' in external_ids and external_ids['BrickLink']:
                bricklink_data = external_ids['BrickLink']

                # Extract BrickLink color ID and name from the nested structure
                if isinstance(bricklink_data, dict):
                    if 'ext_ids' in bricklink_data and bricklink_data['ext_ids']:
                        record['bricklink_color_id'] = bricklink_data['ext_ids'][0]

                    if 'ext_descrs' in bricklink_data and bricklink_data['ext_descrs']:
                        # ext_descrs is a list of lists, get the first description from the first list
                        if len(bricklink_data['ext_descrs']) > 0 and len(bricklink_data['ext_descrs'][0]) > 0:
                            record['bricklink_color_name'] = bricklink_data['ext_descrs'][0][0]

        # Extract BrickLink part number if available
        if 'part' in data and 'external_ids' in data['part']:
            part_external_ids = data['part']['external_ids']
            if 'BrickLink' in part_external_ids and part_external_ids['BrickLink']:
                bricklink_parts = part_external_ids['BrickLink']
                if isinstance(bricklink_parts, list) and len(bricklink_parts) > 0:
                    record['bricklink_part_num'] = bricklink_parts[0]

        if brickset is not None:
            record['id'] = brickset.fields.id

        if minifigure is not None:
            record['figure'] = minifigure.fields.figure

        # Extract the file name
        if record['image'] is not None:
            image_id, _ = os.path.splitext(
                os.path.basename(
                    urlparse(record['image']).path
                )
            )

            if image_id is not None or image_id != '':
                record['image_id'] = image_id

        return record
