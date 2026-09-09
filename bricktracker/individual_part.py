import logging
import os
import traceback
from typing import Any, Self, TYPE_CHECKING
from urllib.parse import urlparse
from uuid import uuid4

from flask import current_app, url_for

from .bricklink_catalog import image_name, ITEM_TYPE_PART
from .exceptions import NotFoundException, DatabaseException, ErrorException
from .record import BrickRecord
from .set_owner_list import BrickSetOwnerList
from .set_purchase_location_list import BrickSetPurchaseLocationList
from .set_storage_list import BrickSetStorageList
from .set_tag_list import BrickSetTagList
from .sql import BrickSQL

if TYPE_CHECKING:
    from .socket import BrickSocket

logger = logging.getLogger(__name__)


# Individual part (standalone, not associated with a set or minifigure)
class IndividualPart(BrickRecord):
    # Queries
    select_query: str = 'individual_part/select/by_id'
    insert_query: str = 'individual_part/insert'
    update_query: str = 'individual_part/update'

    def __init__(
        self,
        /,
        *,
        record: Any | None = None
    ):
        super().__init__()

        # Ingest the record if it has one
        if record is not None:
            self.ingest(record)

    # Select a specific individual part by UUID
    def select_by_id(self, id: str, /) -> Self:
        from .set_owner_list import BrickSetOwnerList
        from .set_status_list import BrickSetStatusList
        from .set_tag_list import BrickSetTagList

        self.fields.id = id
        if not self.select(
            override_query=self.select_query,
            owners=BrickSetOwnerList.as_columns(),
            statuses=BrickSetStatusList.as_columns(all=True),
            tags=BrickSetTagList.as_columns(),
        ):
            raise NotFoundException(
                'Individual part with id "{id}" not found'.format(id=id)
            )
        return self

    # Delete an individual part
    def delete(self, /) -> None:
        sql = BrickSQL()
        sql.executescript(
            'individual_part/delete',
            id=self.fields.id
        )
        sql.commit()

    # Generate HTML ID for form elements
    def html_id(self, prefix: str | None = None, /) -> str:
        components: list[str] = ['individual-part']

        if prefix is not None:
            components.append(prefix)

        components.append(self.fields.part)
        components.append(str(self.fields.color))
        components.append(self.fields.id)

        return '-'.join(components)

    # URL for quantity update
    def url_for_quantity(self, /) -> str:
        return url_for('individual_part.update_quantity', id=self.fields.id)

    # URL for description update
    def url_for_description(self, /) -> str:
        return url_for('individual_part.update_description', id=self.fields.id)

    # URL for problem (missing/damaged) update
    def url_for_problem(self, problem_type: str, /) -> str:
        if problem_type == 'missing':
            return url_for('individual_part.update_missing', id=self.fields.id)
        elif problem_type == 'damaged':
            return url_for('individual_part.update_damaged', id=self.fields.id)
        else:
            raise ValueError(f'Invalid problem type: {problem_type}')

    # URL for checked status update
    def url_for_checked(self, /) -> str:
        return url_for('individual_part.update_checked', id=self.fields.id)

    # URL for purchase date update
    def url_for_purchase_date(self, /) -> str:
        return url_for('individual_part.update_purchase_date', id=self.fields.id)

    # URL for purchase price update
    def url_for_purchase_price(self, /) -> str:
        return url_for('individual_part.update_purchase_price', id=self.fields.id)

    # URL for this part's detail page
    def url(self, /) -> str:
        return url_for('individual_part.details', id=self.fields.id)

    def url_for_delete(self, /) -> str:
        return url_for('individual_part.delete_part', id=self.fields.id)

    def url_for_image(self, /) -> str:
        if current_app.config.get('USE_REMOTE_IMAGES', False):
            if hasattr(self.fields, 'image') and self.fields.image:
                return self.fields.image
            else:
                return current_app.config.get('REBRICKABLE_IMAGE_NIL', '')
        else:
            from .rebrickable_image import RebrickableImage

            # Имя файла берём из каталога, как это делают детали в
            # составе набора. Выводить его из адреса картинки нельзя:
            # у BrickLink цвет лежит в пути, а не в имени, поэтому все
            # цвета одной детали получали бы одно имя и затирали друг
            # друга в кэше.
            image_id = getattr(self.fields, 'image_id', None)

            if not image_id:
                image_id = image_name(
                    ITEM_TYPE_PART,
                    self.fields.part,
                    color=self.fields.color,
                )

            if image_id:
                return RebrickableImage.static_url(image_id, 'PARTS_FOLDER')

            return RebrickableImage.static_url(RebrickableImage.nil_name(), 'PARTS_FOLDER')

    # String representation for debugging
    def __repr__(self, /) -> str:
        """String representation for debugging"""
        part_id = getattr(self.fields, 'part', 'unknown')
        color_id = getattr(self.fields, 'color', 'unknown')
        qty = getattr(self.fields, 'quantity', 0)
        return f'<IndividualPart {part_id} color:{color_id} qty:{qty}>'

    # Get or fetch color information from rebrickable_colors table
    @staticmethod
    def get_or_fetch_color(color_id: int, /) -> dict[str, Any] | None:
        sql = BrickSQL()

        # Check if color exists in cache
        result = sql.fetchone('rebrickable_colors/select/by_color_id', parameters={'color_id': color_id})

        if result:
            # Color found in cache
            return {
                'color_id': result[0],
                'name': result[1],
                'rgb': result[2],
                'is_trans': result[3],
                'bricklink_color_id': result[4],
                'bricklink_color_name': result[5]
            }

        # Цвета нет в кэше: берём из каталога BrickLink
        try:
            from .bricklink_catalog import BrickLinkCatalog

            with BrickLinkCatalog() as catalog:
                color_data = next(
                    (
                        color for color in catalog.colors()
                        if int(color['COLOR']) == color_id
                    ),
                    None,
                )

            if color_data is None:
                return None

            name = color_data['COLORNAME']
            is_trans = color_data['COLORTYPE'] == 'Transparent'

            sql.execute('rebrickable_colors/insert', parameters={
                'color_id': color_id,
                'name': name,
                'rgb': color_data['COLORRGB'],
                'is_trans': is_trans,
                # Каталог теперь и есть BrickLink, переводить нечего
                'bricklink_color_id': color_id,
                'bricklink_color_name': name,
            })
            sql.connection.commit()

            return {
                'color_id': color_id,
                'name': name,
                'rgb': color_data['COLORRGB'],
                'is_trans': is_trans,
                'bricklink_color_id': color_id,
                'bricklink_color_name': name,
            }

        except Exception as e:
            logger.warning('Could not read color {color_id} from the BrickLink catalog: {error}'.format(  # noqa: E501
                color_id=color_id,
                error=e,
            ))
            return None

    # Download image for this part
    def download_image(self, image_url: str, /, *, image_filename: str | None = None) -> None:
        if not image_url:
            return

        # Имя задаётся явно, иначе складывается из детали и цвета.
        # Выводить его из адреса нельзя: цвет туда не попадает.
        if image_filename:
            image_id = image_filename
        else:
            image_id = image_name(
                ITEM_TYPE_PART,
                self.fields.part,
                color=self.fields.color,
            )

        if not image_id:
            return

        # Путь и загрузка общие с картинками каталога: своя загрузка
        # обходилась без заголовка User-Agent, а BrickLink на такие
        # запросы отвечает отказом, и картинка просто не появлялась
        from .rebrickable_image import fetch, RebrickableImage

        fetch(
            image_url,
            RebrickableImage.file_path(image_id, 'PARTS_FOLDER'),
            name=image_id,
        )

    # Load available colors for a part
    def load_colors(self, socket: 'BrickSocket', data: dict[str, Any], /) -> bool:
        # Check if individual parts are disabled
        if current_app.config.get('DISABLE_INDIVIDUAL_PARTS', False):
            socket.fail(message='Individual parts system is disabled.')
            return False

        try:
            # Extract part number
            part_num = str(data.get('part', '')).strip()

            if not part_num:
                raise ErrorException('Part number is required')

            from .bricklink_catalog import (
                BrickLinkCatalog,
                image_url,
                ITEM_TYPE_PART,
            )

            socket.progress_count = 0
            socket.progress_total = 2

            socket.auto_progress(message='Fetching part information')

            with BrickLinkCatalog() as catalog:
                reference = catalog.item(ITEM_TYPE_PART, part_num)

                if reference is None:
                    raise NotFoundException('Part {part_num} was not found in the BrickLink catalog'.format(  # noqa: E501
                        part_num=part_num,
                    ))

                part_name = reference['ITEMNAME']

                socket.auto_progress(message='Fetching available colors')

                # В выгрузке нет перечня цветов, в которых выпускалась
                # деталь: BrickLink держит его только на сайте. Поэтому
                # предлагается весь список цветов, а не отфильтрованный.
                # Картинки заранее не качаются — их 216 на деталь, и почти
                # все оказались бы ненужными.
                colors = [
                    {
                        'color_id': int(color['COLOR']),
                        'color_name': color['COLORNAME'],
                        'part_img_url': image_url(
                            ITEM_TYPE_PART,
                            part_num,
                            color=int(color['COLOR']),
                        ),
                    }
                    for color in catalog.colors()
                ]

            socket.emit(
                'PART_COLORS_LOADED',
                {
                    'part': part_num,
                    'part_name': part_name,
                    'colors': colors,
                    'count': len(colors),
                }
            )

            return True

        except Exception as e:
            error_msg = str(e)
            socket.fail(message=f'Could not load part colors: {error_msg}')

            if not isinstance(e, (NotFoundException, ErrorException)):
                logger.debug(traceback.format_exc())

            return False

    # Add a new individual part
    def add(self, socket: 'BrickSocket', data: dict[str, Any], /) -> bool:
        # Check if individual parts are disabled
        if current_app.config.get('DISABLE_INDIVIDUAL_PARTS', False):
            socket.fail(message='Individual parts system is disabled.')
            return False

        try:
            # Reset progress
            socket.progress_count = 0
            socket.progress_total = 3

            socket.auto_progress(message='Validating part and color')

            # Extract data
            part_num = str(data.get('part', '')).strip()
            color_id = int(data.get('color', -1))
            quantity = int(data.get('quantity', 1))

            if not part_num:
                raise ErrorException('Part number is required')
            if color_id < 0:
                raise ErrorException('Valid color ID is required')
            if quantity <= 0:
                raise ErrorException('Quantity must be greater than 0')

            # Check if color info was pre-loaded (from load_colors)
            color_data = data.get('color_info', None)
            part_name = data.get('part_name', None)

            # Validate part+color exists in rebrickable_parts
            # If not, fetch from Rebrickable or use pre-loaded data and insert
            sql = BrickSQL()
            result = sql.fetchone('rebrickable_parts/check_exists', parameters={'part': part_num, 'color_id': color_id})
            exists = result[0] > 0

            # Store image URL for downloading later
            image_url = None

            if not exists:
                # Fetch full color information (with BrickLink mapping)
                socket.auto_progress(message='Fetching color information')
                full_color_info = IndividualPart.get_or_fetch_color(color_id)

                # If we have pre-loaded color data, use it; otherwise fetch from Rebrickable
                if color_data and part_name:
                    # Use pre-loaded data from get_part_colors() response
                    socket.auto_progress(message='Using cached part info')

                    image_url = color_data.get('part_img_url', '')

                    # Имя в кэше складывается из детали и цвета:
                    # идентификаторов элементов у BrickLink нет, а адрес
                    # картинки цвета в имени не содержит
                    image_id = image_name(
                        ITEM_TYPE_PART,
                        part_num,
                        color=color_id,
                    )

                    # Insert into rebrickable_parts using the pre-loaded data
                    sql.execute('rebrickable_parts/insert_with_preloaded_data', parameters={
                        'part': part_num,
                        'color_id': color_id,
                        'color_name': color_data.get('color_name', ''),
                        'color_rgb': full_color_info.get('rgb') if full_color_info else None,
                        'color_transparent': full_color_info.get('is_trans') if full_color_info else None,
                        'bricklink_color_id': full_color_info.get('bricklink_color_id') if full_color_info else None,
                        'bricklink_color_name': full_color_info.get('bricklink_color_name') if full_color_info else None,
                        'name': part_name,
                        'image': image_url,
                        'image_id': image_id,
                        'url': current_app.config['BRICKLINK_LINK_PART_PATTERN'].format(part=part_num, color=color_id)  # noqa: E501
                    })
                else:
                    # Данных с шага выбора цвета нет: берём из каталога
                    socket.auto_progress(
                        message='Fetching part info from the BrickLink catalog',  # noqa: E501
                    )

                    from .bricklink_catalog import (
                        BrickLinkCatalog,
                        image_url as bricklink_image_url,
                    )

                    with BrickLinkCatalog() as catalog:
                        reference = catalog.item(ITEM_TYPE_PART, part_num)

                    if reference is None:
                        raise NotFoundException('Part {part_num} was not found in the BrickLink catalog'.format(  # noqa: E501
                            part_num=part_num,
                        ))

                    if not full_color_info:
                        full_color_info = IndividualPart.get_or_fetch_color(
                            color_id,
                        )

                    image_url = bricklink_image_url(
                        ITEM_TYPE_PART,
                        part_num,
                        color=color_id,
                    )
                    image_id = image_name(
                        ITEM_TYPE_PART,
                        part_num,
                        color=color_id,
                    )

                    sql.execute('rebrickable_parts/insert_with_preloaded_data', parameters={  # noqa: E501
                        'part': part_num,
                        'color_id': color_id,
                        'color_name': full_color_info['name'] if full_color_info else '',  # noqa: E501
                        'color_rgb': full_color_info['rgb'] if full_color_info else None,  # noqa: E501
                        'color_transparent': full_color_info['is_trans'] if full_color_info else None,  # noqa: E501
                        'bricklink_color_id': color_id,
                        'bricklink_color_name': full_color_info['name'] if full_color_info else '',  # noqa: E501
                        'name': reference['ITEMNAME'],
                        'image': image_url,
                        'image_id': image_id,
                        'url': current_app.config['BRICKLINK_LINK_PART_PATTERN'].format(  # noqa: E501
                            part=part_num,
                            color=color_id,
                        ),
                    })
            else:
                # Part already exists in rebrickable_parts, get the image URL
                result = sql.fetchone('rebrickable_parts/select/image_by_part_color', parameters={'part': part_num, 'color_id': color_id})
                if result and result[0]:
                    image_url = result[0]

            # Generate UUID and insert individual part
            socket.auto_progress(message='Adding part to collection')
            part_id = str(uuid4())

            # Get storage and purchase location
            storage = BrickSetStorageList.get(
                data.get('storage', ''),
                allow_none=True
            )
            purchase_location = BrickSetPurchaseLocationList.get(
                data.get('purchase_location', ''),
                allow_none=True
            )

            # Set fields
            self.fields.id = part_id
            self.fields.part = part_num
            self.fields.color = color_id
            self.fields.quantity = quantity
            self.fields.missing = 0
            self.fields.damaged = 0
            self.fields.checked = 0
            self.fields.description = data.get('description', '')
            self.fields.lot_id = None  # Single parts are not in a lot
            self.fields.storage = storage.fields.id if storage else None
            self.fields.purchase_location = purchase_location.fields.id if purchase_location else None
            self.fields.purchase_date = data.get('purchase_date', None)
            self.fields.purchase_price = data.get('purchase_price', None)

            # Insert into database
            self.insert(commit=False, no_defer=True)

            # Save owners
            owners: list[str] = list(data.get('owners', []))
            for owner_id in owners:
                owner = BrickSetOwnerList.get(owner_id)
                owner.update_individual_part_state(self, state=True)

            # Save tags
            tags: list[str] = list(data.get('tags', []))
            for tag_id in tags:
                tag = BrickSetTagList.get(tag_id)
                tag.update_individual_part_state(self, state=True)

            # Commit
            sql.connection.commit()

            # Download image if we have a URL
            if image_url:
                try:
                    self.download_image(image_url)
                except Exception as e:
                    # Don't fail the whole operation if image download fails
                    logger.warning('Could not download image for part {part_num} color {color_id}: {error}'.format(
                        part_num=part_num,
                        color_id=color_id,
                        error=e
                    ))

            # Get color name for success message
            color_name = 'Unknown'
            if color_data and color_data.get('color_name'):
                color_name = color_data.get('color_name')
            elif full_color_info and full_color_info.get('name'):
                color_name = full_color_info.get('name')

            # Generate link to part details page
            part_url = url_for('part.details', part=part_num, color=color_id)

            socket.complete(
                message=f'Successfully added part {part_num} in {color_name} (<a href="{part_url}">View details</a>)'
            )
            return True

        except Exception as e:
            error_msg = str(e)
            if 'Individual parts system is disabled' in error_msg:
                socket.fail(message=error_msg)
            else:
                socket.fail(
                    message=f'Could not add individual part: {error_msg}'
                )

            if not isinstance(e, (NotFoundException, ErrorException)):
                logger.debug(traceback.format_exc())

            return False

    # Create multiple individual parts (bulk mode - no lot)
    def create_bulk(self, socket: 'BrickSocket', data: dict[str, Any], /) -> bool:
        """
        Create multiple individual parts without creating a lot.

        Expected data format:
        {
            'cart': [
                {
                    'part': '3001',
                    'part_name': 'Brick 2 x 4',
                    'color_id': 1,
                    'color_name': 'White',
                    'quantity': 10,
                    'color_info': {...}
                },
                ...
            ],
            'storage': 'storage_id',
            'purchase_location': 'purchase_location_id',
            'purchase_date': timestamp,
            'purchase_price': 0.0,
            'owners': ['owner_id1', ...],
            'tags': ['tag_id1', ...]
        }
        """
        try:
            # Validate cart data
            cart = data.get('cart', [])
            if not cart or not isinstance(cart, list):
                raise ErrorException('Cart is empty or invalid')

            socket.auto_progress(
                message=f'Adding {len(cart)} individual parts',
                increment_total=True
            )

            # Get storage
            from .set_list import BrickSetStorageList, BrickSetPurchaseLocationList, BrickSetOwnerList, BrickSetTagList
            storage = BrickSetStorageList.get(
                data.get('storage', ''),
                allow_none=True
            )
            storage_id = storage.fields.id if storage else None

            # Get purchase location
            purchase_location = BrickSetPurchaseLocationList.get(
                data.get('purchase_location', ''),
                allow_none=True
            )
            purchase_location_id = purchase_location.fields.id if purchase_location else None

            # Get purchase info
            purchase_date = data.get('purchase_date', None)
            purchase_price = data.get('purchase_price', None)

            # Get owners and tags
            owners: list[str] = list(data.get('owners', []))
            tags: list[str] = list(data.get('tags', []))

            # Add all parts from cart
            parts_added = 0
            for idx, cart_item in enumerate(cart):
                part_num = cart_item.get('part')
                color_id = cart_item.get('color_id')
                quantity = cart_item.get('quantity', 1)
                color_info = cart_item.get('color_info', {})

                socket.auto_progress(
                    message=f'Adding part {idx + 1}/{len(cart)}: {part_num} in {cart_item.get("color_name", "unknown color")}',
                    increment_total=True
                )

                # Create individual part with no lot_id
                part_uuid = str(uuid4())

                # Ensure color exists and get full color info (including RGB)
                full_color_info = IndividualPart.get_or_fetch_color(color_id)

                # Insert the part
                sql = BrickSQL()

                # Ensure part/color combination exists in rebrickable_parts (same as lot creation)
                try:
                    # Check if part exists
                    result = sql.fetchone('rebrickable_parts/check_exists', parameters={'part': part_num, 'color_id': color_id})
                    exists = result[0] > 0

                    if not exists:
                        # Insert part data
                        part_name = cart_item.get('part_name', '')
                        color_name = cart_item.get('color_name', '')
                        image_url = color_info.get('part_img_url', '')

                        image_id = image_name(
                            ITEM_TYPE_PART,
                            part_num,
                            color=color_id,
                        )

                        # Use full_color_info for RGB and transparency data (same as single-part add)
                        sql.execute('rebrickable_parts/insert_part_color', parameters={
                            'part': part_num,
                            'name': part_name,
                            'color_id': color_id,
                            'color_name': color_name,
                            'color_rgb': full_color_info.get('rgb') if full_color_info else '',
                            'color_transparent': full_color_info.get('is_trans') if full_color_info else False,
                            'image': image_url,
                            'image_id': image_id,
                            'url': current_app.config['REBRICKABLE_LINK_PART_PATTERN'].format(part=part_num, color=color_id),
                            'bricklink_color_id': full_color_info.get('bricklink_color_id') if full_color_info else None,
                            'bricklink_color_name': full_color_info.get('bricklink_color_name') if full_color_info else None
                        })
                except Exception as e:
                    logger.warning('Could not ensure part data for {part_num}/{color_id}: {error}'.format(
                        part_num=part_num,
                        color_id=color_id,
                        error=e
                    ))

                # Insert individual part
                sql.execute(
                    'individual_part/insert',
                    parameters={
                        'id': part_uuid,
                        'part': part_num,
                        'color': color_id,
                        'quantity': quantity,
                        'lot_id': None,  # No lot - this is bulk individual parts mode
                        'storage': storage_id,
                        'purchase_location': purchase_location_id,
                        'purchase_date': purchase_date,
                        'purchase_price': purchase_price,
                        'description': None,
                        'missing': 0,
                        'damaged': 0,
                        'checked': False
                    }
                )

                # Add owners
                for owner_id in owners:
                    owner = BrickSetOwnerList.get(owner_id)
                    if owner:
                        sql.execute(
                            'individual_part/metadata/owner/insert',
                            parameters={
                                'part_id': part_uuid,
                                'owner_id': owner_id
                            }
                        )

                # Add tags
                for tag_id in tags:
                    tag = BrickSetTagList.get(tag_id)
                    if tag:
                        sql.execute(
                            'individual_part/metadata/tag/insert',
                            parameters={
                                'part_id': part_uuid,
                                'tag_id': tag_id
                            }
                        )

                # Download part image if available
                image_url = color_info.get('part_img_url', '')
                if image_url:
                    try:
                        self.download_image(image_url)
                    except Exception as e:
                        # Don't fail the whole operation if image download fails
                        logger.warning('Could not download image for part {part_num} color {color_id}: {error}'.format(
                            part_num=part_num,
                            color_id=color_id,
                            error=e
                        ))

                parts_added += 1

            # Commit all changes
            sql = BrickSQL()
            sql.commit()

            socket.auto_progress(
                message=f'Successfully added {parts_added} individual parts',
                increment_total=True
            )

            # Generate link to individual parts list
            from flask import url_for
            parts_url = url_for('individual_part.list')

            # Send completion with message and link
            socket.complete(
                message='Successfully added {count} individual parts. <a href="{url}">View individual parts</a>'.format(
                    count=parts_added,
                    url=parts_url
                ),
                parts_added=parts_added
            )
            return True

        except ErrorException as error:
            socket.fail(message=str(error))
            return False
        except Exception as error:
            logger.error('Failed to create bulk individual parts: {error}'.format(error=error))
            logger.error(traceback.format_exc())
            socket.fail(message='Failed to add individual parts: {error}'.format(error=str(error)))
            return False

    # Update a field
    def update_field(self, field: str, value: Any, /) -> Self:
        setattr(self.fields, field, value)

        # Use a specific update query for each field
        sql = BrickSQL()
        sql.execute_and_commit('individual_part/update/field', parameters={
            'id': self.fields.id,
            'value': value
        }, field=field)

        return self

    # Update problem count (missing/damaged)
    def update_problem(self, problem: str, data: dict[str, Any], /) -> int:
        # Handle both 'value' key and 'amount' key
        amount: str | int = data.get('value', data.get('amount', ''))  # type: ignore

        # We need a positive integer
        try:
            if amount == '':
                amount = 0

            amount = int(amount)

            if amount < 0:
                amount = 0
        except Exception:
            raise ErrorException(f'"{amount}" is not a valid integer')

        if amount < 0:
            raise ErrorException('Cannot set a negative amount')

        setattr(self.fields, problem, amount)

        BrickSQL().execute_and_commit(
            f'individual_part/update/{problem}',
            parameters={
                'id': self.fields.id,
                problem: amount
            }
        )

        return amount

    # Update checked status
    def update_checked(self, data: dict[str, Any], /) -> bool:
        # Handle both direct 'checked' key and changer.js 'value' key format
        if data:
            checked = data.get('checked', data.get('value', False))
        else:
            checked = False

        checked = bool(checked)
        self.fields.checked = 1 if checked else 0

        BrickSQL().execute_and_commit(
            'individual_part/update/checked',
            parameters={
                'id': self.fields.id,
                'checked': self.fields.checked
            }
        )

        return checked
