import logging
import os
import traceback
from datetime import datetime
from typing import Any, Self, TYPE_CHECKING
from urllib.parse import urlparse
from uuid import uuid4

from flask import (
    current_app,
    url_for,
)
from werkzeug.datastructures import FileStorage

from .exceptions import NotFoundException, DatabaseException, ErrorException
from .individual_part import IndividualPart
from .record import BrickRecord, format_timestamp
from .set_owner_list import BrickSetOwnerList
from .set_purchase_location_list import BrickSetPurchaseLocationList
from .set_storage_list import BrickSetStorageList
from .set_tag_list import BrickSetTagList
from .sql import BrickSQL

if TYPE_CHECKING:
    from .socket import BrickSocket

logger = logging.getLogger(__name__)


# Individual part lot (collection/batch of individual parts added together)
class IndividualPartLot(BrickRecord):
    # Queries
    select_query: str = 'individual_part_lot/select/by_id'
    insert_query: str = 'individual_part_lot/insert'

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

    # Select a specific lot by UUID
    def select_by_id(self, id: str, /) -> Self:
        from .set_owner_list import BrickSetOwnerList
        from .set_tag_list import BrickSetTagList

        self.fields.id = id
        if not self.select(
            override_query=self.select_query,
            owners=BrickSetOwnerList.as_columns(),
            tags=BrickSetTagList.as_columns(),
            # Note: Part lots don't have statuses (by design)
            # Statuses are meant for tracking set completion/verification, which doesn't apply
            # to loose part collections. Individual parts within lots can still be marked as
            # missing/damaged/checked through the parts inventory system.
        ):
            raise NotFoundException(
                'Individual part lot with id "{id}" not found'.format(id=id)
            )
        return self

    # Delete a lot and all its parts
    def delete(self, /) -> None:
        # Картинку убираем до строки: после удаления имя файла взять
        # будет негде, и он остался бы в папке навсегда
        self.delete_image()

        BrickSQL().executescript(
            'individual_part_lot/delete',
            id=self.fields.id
        )

    # Get the URL for this lot
    def url(self, /) -> str:
        return url_for('individual_part.lot_details', lot_id=self.fields.id)

    # -- Своя картинка ----------------------------------------------------

    # Есть ли у лота своя картинка
    #
    # Проверяется и файл: строка могла пережить папку данных, и тогда
    # карточка показала бы битую картинку вместо мозаики из деталей.
    def has_image(self, /) -> bool:
        name = getattr(self.fields, 'image', None)

        if not name:
            return False

        return os.path.isfile(self.image_path(name))

    # Путь к файлу картинки
    @staticmethod
    def image_path(name: str, /) -> str:
        folder: str = current_app.config['LOTS_FOLDER']

        if not folder.startswith('/'):
            folder = os.path.join(current_app.root_path, folder)

        return os.path.join(folder, name)

    # Адрес картинки для страницы
    def url_for_image(self, /) -> str:
        return url_for(
            'data.serve_data_file',
            folder='lots',
            filename=self.fields.image,
        )

    # Сохранить загруженную картинку
    #
    # Имя файла — идентификатор лота: так он не столкнётся с чужим и не
    # утащит в папку данных то, как файл назывался у пользователя.
    # Расширение остаётся исходным, чтобы не перекодировать картинку.
    def save_image(self, file: FileStorage, /) -> None:
        _, extension = os.path.splitext(file.filename or '')

        name = '{id}{extension}'.format(
            id=self.fields.id,
            extension=extension.lower(),
        )

        path = self.image_path(name)

        os.makedirs(os.path.dirname(path), exist_ok=True)

        file.save(path)

        # Прежняя картинка могла быть с другим расширением: тогда новая её
        # не перезаписала, и старый файл надо убрать самим
        previous = getattr(self.fields, 'image', None)

        if previous and previous != name:
            self.remove_image_file(previous)

        self.fields.image = name

        BrickSQL().execute_and_commit(
            'individual_part_lot/update/image',
            parameters={'id': self.fields.id, 'image': name},
        )

        logger.info('Individual part lot {id}: image saved as {name}'.format(
            id=self.fields.id,
            name=name,
        ))

    # Убрать картинку: и файл, и строку
    def delete_image(self, /) -> None:
        name = getattr(self.fields, 'image', None)

        if not name:
            return

        self.remove_image_file(name)

        self.fields.image = None

        BrickSQL().execute_and_commit(
            'individual_part_lot/update/image',
            parameters={'id': self.fields.id, 'image': None},
        )

        logger.info('Individual part lot {id}: image removed'.format(
            id=self.fields.id,
        ))

    # Удалить файл картинки, не трогая базу
    @classmethod
    def remove_image_file(cls, name: str, /) -> None:
        try:
            os.remove(cls.image_path(name))
        except OSError as e:
            # Файла может не быть: папку данных могли почистить руками.
            # Это не повод ронять удаление лота.
            logger.warning('Could not remove lot image {name}: {error}'.format(
                name=name,
                error=e,
            ))

    # String representation for debugging
    def __repr__(self, /) -> str:
        name = getattr(self.fields, 'name', 'Unnamed') or 'Unnamed'
        lot_id = getattr(self.fields, 'id', 'unknown')
        # Try to get part_count if available (from optimized query)
        part_count = getattr(self.fields, 'part_count', '?')
        return f'<IndividualPartLot "{name}" ({part_count} parts) id:{lot_id[:8]}...>'

    # Format created date
    def created_date_formatted(self, /) -> str:
        return format_timestamp(self.fields.created_date)

    # Format purchase date
    def purchase_date_formatted(self, /) -> str:
        return format_timestamp(self.fields.purchase_date)

    # Format purchase price
    def purchase_price(self, /) -> str:
        from flask import current_app
        if self.fields.purchase_price is not None:
            return '{price}{currency}'.format(
                price=self.fields.purchase_price,
                currency=current_app.config['PURCHASE_CURRENCY']
            )
        else:
            return ''

    # Get all parts in this lot
    def parts(self, /) -> list['IndividualPart']:
        sql = BrickSQL()
        parts_data = sql.fetchall('individual_part_lot/list/parts', parameters={'lot_id': self.fields.id})

        # Convert to list of IndividualPart objects using ingest()
        return [IndividualPart(record=record) for record in parts_data]

    # Get total quantity of all parts in this lot
    def total_quantity(self, /) -> int:
        parts = self.parts()
        return sum(part.fields.quantity for part in parts)

    # Create a new lot with parts from cart
    def create(self, socket: 'BrickSocket', data: dict[str, Any], /) -> bool:
        """
        Create a new individual part lot with multiple parts.

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
            'name': 'Optional lot name',
            'description': 'Optional lot description',
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
                message=f'Creating lot with {len(cart)} parts',
                increment_total=True
            )

            # Generate UUID for the lot
            lot_id = str(uuid4())
            self.fields.id = lot_id

            # Set lot metadata
            self.fields.name = data.get('name', None)
            self.fields.description = data.get('description', None)
            self.fields.created_date = datetime.now().timestamp()

            # Get storage
            storage = BrickSetStorageList.get(
                data.get('storage', ''),
                allow_none=True
            )
            self.fields.storage = storage.fields.id if storage else None

            # Get purchase location
            purchase_location = BrickSetPurchaseLocationList.get(
                data.get('purchase_location', ''),
                allow_none=True
            )
            self.fields.purchase_location = purchase_location.fields.id if purchase_location else None

            # Set purchase info
            self.fields.purchase_date = data.get('purchase_date', None)
            self.fields.purchase_price = data.get('purchase_price', None)

            # Insert the lot record
            socket.auto_progress(
                message='Inserting lot into database',
                increment_total=True
            )
            self.insert(commit=False)

            # Commit the lot so parts can reference it
            sql = BrickSQL()
            sql.commit()

            # Save owners using the metadata update methods
            owners: list[str] = list(data.get('owners', []))
            for owner_id in owners:
                owner = BrickSetOwnerList.get(owner_id)
                if owner:
                    owner.update_individual_part_lot_state(self, state=True, commit=False)

            # Save tags using the metadata update methods
            tags: list[str] = list(data.get('tags', []))
            for tag_id in tags:
                tag = BrickSetTagList.get(tag_id)
                if tag:
                    tag.update_individual_part_lot_state(self, state=True, commit=False)

            # Add all parts from cart
            socket.auto_progress(
                message=f'Adding {len(cart)} parts to lot',
                increment_total=True
            )

            for idx, cart_item in enumerate(cart):
                part_num = cart_item.get('part')
                color_id = cart_item.get('color_id')
                quantity = cart_item.get('quantity', 1)
                color_info = cart_item.get('color_info', {})

                socket.auto_progress(
                    message=f'Adding part {idx + 1}/{len(cart)}: {part_num} in {cart_item.get("color_name", "unknown color")}',
                    increment_total=True
                )

                # Create individual part with lot_id
                part_uuid = str(uuid4())
                sql = BrickSQL()

                # Ensure color and part/color combination exist in rebrickable tables
                IndividualPart.get_or_fetch_color(color_id)
                part_name = cart_item.get('part_name', '')
                color_name = cart_item.get('color_name', '')
                image_url = color_info.get('part_img_url', '')

                # Extract image_id from element_ids or URL
                element_ids = color_info.get('elements', [])
                if element_ids and len(element_ids) > 0:
                    image_id = str(element_ids[0])
                elif image_url:
                    image_id, _ = os.path.splitext(os.path.basename(urlparse(image_url).path))
                else:
                    image_id = None

                sql.execute('rebrickable_parts/insert_part_color', parameters={
                    'part': part_num,
                    'name': part_name,
                    'color_id': color_id,
                    'color_name': color_name,
                    'color_rgb': color_info.get('rgb', ''),
                    'color_transparent': color_info.get('is_trans', False),
                    'image': image_url,
                    'image_id': image_id,
                    'url': current_app.config['REBRICKABLE_LINK_PART_PATTERN'].format(part=part_num, color=color_id),
                    'bricklink_color_id': color_info.get('bricklink_color_id', None),
                    'bricklink_color_name': color_info.get('bricklink_color_name', None)
                })
                # Commit so the foreign key constraint can be satisfied
                sql.commit()

                # Now insert the part with lot_id (NO individual metadata - inherited from lot)
                sql.execute('individual_part/insert_with_lot', parameters={
                    'id': part_uuid,
                    'part': part_num,
                    'color': color_id,
                    'quantity': quantity,
                    'lot_id': lot_id
                })

            # Commit all changes
            socket.auto_progress(
                message='Committing changes to database',
                increment_total=True
            )
            sql.commit()

            socket.auto_progress(
                message=f'Lot created successfully with {len(cart)} parts',
                increment_total=True
            )

            # Complete with success message and lot URL
            lot_url = self.url()
            socket.complete(
                message=f'Successfully created lot with {len(cart)} parts. <a href="{lot_url}">View lot</a>',
                data={
                    'lot_id': lot_id,
                    'lot_url': lot_url
                }
            )

            return True

        except ErrorException as e:
            socket.fail(message=str(e))
            logger.error('Error creating lot: {error}'.format(error=e))
            return False
        except Exception as e:
            socket.fail(message='Unexpected error creating lot: {error}'.format(error=str(e)))
            logger.error('Unexpected error creating lot: {error}'.format(error=e))
            logger.error(traceback.format_exc())
            return False
