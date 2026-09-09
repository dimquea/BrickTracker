from datetime import datetime, timezone
from typing import Any
from uuid import uuid4
from xml.etree import ElementTree
import logging

from flask import current_app

from .bricklink import BrickLink
from .bricklink_catalog import (
    BrickLinkCatalog,
    image_name,
    image_url,
    ITEM_TYPE_PART,
)
from .exceptions import ErrorException
from .rebrickable_image import fetch, RebrickableImage
from .sql import BrickSQL

logger = logging.getLogger(__name__)


# Импорт списка деталей из BrickLink XML
#
# Формат тот же, в котором приложение выгружает Wanted List, так что
# выгруженное можно загрузить обратно. Его же отдают BrickStore и сам
# BrickLink, поэтому разобранный набор или купленная партия попадают в
# коллекцию файлом, а не поштучно через корзину.
#
# Позиции становятся отдельными деталями. При указанном имени лота они
# складываются в новый лот: у партии обычно общие дата, цена и источник,
# а лот ровно для этого и заведён.
class BrickLinkImport(object):
    # Позиции, которые удалось разобрать
    entries: list[dict[str, Any]]

    # Строки, которые не удалось разобрать или принять, с причиной
    skipped: list[dict[str, str]]

    # Позиции, для которых не удалось сложить картинку в кэш
    images_failed: list[str]

    def __init__(self, /):
        self.entries = []
        self.skipped = []
        self.images_failed = []

    # -- Разбор -----------------------------------------------------------

    # Разобрать содержимое файла
    #
    # Из всего разнообразия Wanted List нас интересуют три поля. Количество
    # приходит то в MINQTY, то в QTY, в зависимости от того, кто выгружал.
    def parse(self, content: bytes, /) -> None:
        try:
            root = ElementTree.fromstring(content)
        except ElementTree.ParseError as e:
            raise ErrorException('The file is not readable as XML: {error}'.format(  # noqa: E501
                error=e,
            ))

        items = root.findall('.//ITEM')

        if not items:
            raise ErrorException('No ITEM entries found: this does not look like a BrickLink XML file')  # noqa: E501

        for item in items:
            def field(name: str, /) -> str:
                node = item.find(name)

                if node is None or node.text is None:
                    return ''

                return node.text.strip()

            identifier = field('ITEMID')

            if not identifier:
                self.skipped.append({
                    'item': '(empty)',
                    'reason': 'no ITEMID',
                })
                continue

            item_type = field('ITEMTYPE') or ITEM_TYPE_PART

            # Фигурки и наборы в списке встречаются, но заводятся иначе:
            # у фигурки свой состав, у набора инвентарь. Молча проглотить
            # их было бы хуже, чем сказать.
            if item_type != ITEM_TYPE_PART:
                self.skipped.append({
                    'item': identifier,
                    'reason': 'not a part (ITEMTYPE {type}), add it from its own page'.format(  # noqa: E501
                        type=item_type,
                    ),
                })
                continue

            try:
                color = int(field('COLOR') or 0)
                quantity = int(field('MINQTY') or field('QTY') or 1)
            except ValueError:
                self.skipped.append({
                    'item': identifier,
                    'reason': 'colour or quantity is not a number',
                })
                continue

            if quantity < 1:
                self.skipped.append({
                    'item': identifier,
                    'reason': 'quantity is not positive',
                })
                continue

            self.entries.append({
                'part': identifier,
                'color': color,
                'quantity': quantity,
            })

    # -- Применение -------------------------------------------------------

    # Записать разобранное в базу
    #
    # Возвращает число добавленных позиций. Всё, что не нашлось в каталоге,
    # уходит в skipped: коллекция не должна пополняться артикулами, о
    # которых мы ничего не знаем.
    #
    # Картинки складываются в кэш здесь же. Раньше импорт их не трогал
    # вовсе: в каталожную строку записывался адрес, а файла не появлялось,
    # и на странице висела битая картинка — кроме тех деталей, чей цвет
    # уже встречался в наборах коллекции.
    def apply(self, /, *, lot: dict[str, Any] | None = None) -> int:
        if not self.entries:
            return 0

        with BrickLinkCatalog() as catalog:
            reference = BrickLink.reference(
                catalog,
                ITEM_TYPE_PART,
                {entry['part'] for entry in self.entries},
            )
            colors = BrickLink.colors(catalog)

        sql = BrickSQL()
        lot_id = self.create_lot(sql, lot) if lot else None
        added = 0

        for entry in self.entries:
            part = entry['part']
            color = entry['color']

            if part not in reference:
                self.skipped.append({
                    'item': part,
                    'reason': 'not found in the BrickLink catalog',
                })
                continue

            if color not in colors:
                self.skipped.append({
                    'item': part,
                    'reason': 'unknown colour {color}'.format(color=color),
                })
                continue

            self.ensure_catalog_row(
                sql,
                reference[part],
                colors[color],
                part,
                color,
            )

            if not self.cache_image(part, color):
                self.images_failed.append(part)

            sql.execute(
                'individual_part/insert_with_lot',
                parameters={
                    'id': str(uuid4()),
                    'part': part,
                    'color': color,
                    'quantity': entry['quantity'],
                    'lot_id': lot_id,
                },
                commit=False,
            )

            added += 1

        sql.connection.commit()

        return added

    # Сложить картинку детали в локальный кэш
    #
    # При удалённых картинках кэш не нужен: страница ходит прямо в
    # BrickLink.
    @staticmethod
    def cache_image(part: str, color: int, /) -> bool:
        if current_app.config['USE_REMOTE_IMAGES']:
            return True

        identifier = image_name(ITEM_TYPE_PART, part, color=color)

        return fetch(
            image_url(ITEM_TYPE_PART, part, color=color),
            RebrickableImage.file_path(identifier, 'PARTS_FOLDER'),
            name=identifier,
        )

    # Завести лот под партию
    @staticmethod
    def create_lot(sql: BrickSQL, lot: dict[str, Any], /) -> str:
        lot_id = str(uuid4())

        sql.execute(
            'individual_part_lot/insert',
            parameters={
                'id': lot_id,
                'name': lot.get('name'),
                'description': lot.get('description'),
                'created_date': datetime.now(timezone.utc).timestamp(),
                'storage': lot.get('storage') or None,
                'purchase_location': lot.get('purchase_location') or None,
                'purchase_date': lot.get('purchase_date'),
                'purchase_price': lot.get('purchase_price'),
            },
            commit=False,
        )

        return lot_id

    # Убедиться, что пара деталь-цвет есть в каталоге
    #
    # Внешний ключ отдельных деталей смотрит именно туда, так что без этой
    # строки вставка не пройдёт.
    @staticmethod
    def ensure_catalog_row(
        sql: BrickSQL,
        reference: dict[str, str],
        color: dict[str, str],
        part: str,
        color_id: int,
        /,
    ) -> None:
        result = sql.fetchone(
            'rebrickable_parts/check_exists',
            parameters={'part': part, 'color_id': color_id},
        )

        if result and result[0] > 0:
            return

        sql.execute(
            'rebrickable_parts/insert_part_color',
            parameters={
                'part': part,
                'name': reference.get('ITEMNAME', part),
                'color_id': color_id,
                'color_name': color.get('COLORNAME', ''),
                'color_rgb': color.get('COLORRGB', ''),
                'color_transparent': color.get('COLORTYPE', '') == 'Transparent',  # noqa: E501
                'image': image_url(ITEM_TYPE_PART, part, color=color_id),
                'image_id': image_name(ITEM_TYPE_PART, part, color=color_id),
                'url': current_app.config['BRICKLINK_LINK_PART_PATTERN'].format(  # noqa: E501
                    part=part,
                    color=color_id,
                ),
                # Каталог теперь и есть BrickLink, переводить нечего
                'bricklink_color_id': color_id,
                'bricklink_color_name': color.get('COLORNAME', ''),
            },
            commit=False,
        )
