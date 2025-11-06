import logging
import traceback
from typing import Any, Self, TYPE_CHECKING
from uuid import uuid4

from flask import url_for

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
        self.fields.id = id
        if not self.select(override_query=self.select_query):
            raise NotFoundException(
                'Individual part lot with id "{id}" not found'.format(id=id)
            )
        return self

    # Delete a lot and all its parts
    def delete(self, /) -> None:
        BrickSQL().executescript(
            'individual_part_lot/delete',
            id=self.fields.id
        )

    # Get the URL for this lot
    def url(self, /) -> str:
        return url_for('individual_part.lot_details', lot_id=self.fields.id)

    # String representation for debugging
    def __repr__(self, /) -> str:
        """String representation for debugging"""
        name = getattr(self.fields, 'name', 'Unnamed') or 'Unnamed'
        lot_id = getattr(self.fields, 'id', 'unknown')
        # Try to get part_count if available (from optimized query)
        part_count = getattr(self.fields, 'part_count', '?')
        return f'<IndividualPartLot "{name}" ({part_count} parts) id:{lot_id[:8]}...>'

    # Format created date
    def created_date_formatted(self, /) -> str:
        """Format the created date for display"""
        return format_timestamp(self.fields.created_date)

    # Format purchase date
    def purchase_date_formatted(self, /) -> str:
        """Format the purchase date for display"""
        return format_timestamp(self.fields.purchase_date)

    # Get all parts in this lot
    def parts(self, /) -> list['IndividualPart']:
        """Get all individual parts that belong to this lot"""
        sql = BrickSQL()
        parts_data = sql.fetchall('individual_part_lot/list/parts', lot_id=self.fields.id)

        # Convert to list of IndividualPart objects using ingest()
        return [IndividualPart(record=record) for record in parts_data]

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

            # Save owners
            owners: list[str] = list(data.get('owners', []))
            for owner_id in owners:
                owner = BrickSetOwnerList.get(owner_id)
                # Insert into junction table
                sql = BrickSQL()
                sql.cursor.execute(
                    'INSERT INTO "bricktracker_individual_part_lot_owners" ("id") VALUES (:id)',
                    {'id': lot_id}
                )

            # Save tags
            tags: list[str] = list(data.get('tags', []))
            for tag_id in tags:
                tag = BrickSetTagList.get(tag_id)
                # Insert into junction table
                sql = BrickSQL()
                sql.cursor.execute(
                    'INSERT INTO "bricktracker_individual_part_lot_tags" ("id") VALUES (:id)',
                    {'id': lot_id}
                )

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

                # Use the add method but with lot_id
                # We need to insert the part with the lot_id
                sql = BrickSQL()

                # First ensure the part exists in rebrickable_parts
                IndividualPart.get_or_fetch_color(color_id)

                # Insert the part with lot_id (NO individual metadata - inherited from lot)
                insert_query = """
                    INSERT INTO "bricktracker_individual_parts" (
                        "id",
                        "part",
                        "color",
                        "quantity",
                        "missing",
                        "damaged",
                        "checked",
                        "description",
                        "storage",
                        "purchase_location",
                        "purchase_date",
                        "purchase_price",
                        "lot_id"
                    ) VALUES (
                        :id,
                        :part,
                        :color,
                        :quantity,
                        0,
                        0,
                        0,
                        NULL,
                        NULL,
                        NULL,
                        NULL,
                        NULL,
                        :lot_id
                    )
                """

                sql.cursor.execute(insert_query, {
                    'id': part_uuid,
                    'part': part_num,
                    'color': color_id,
                    'quantity': quantity,
                    'lot_id': lot_id
                })

                # Ensure part data is in rebrickable_parts
                try:
                    # Check if part exists
                    check_query = """
                        SELECT COUNT(*) FROM "rebrickable_parts"
                        WHERE "part" = :part AND "color_id" = :color_id
                    """
                    sql.cursor.execute(check_query, {'part': part_num, 'color_id': color_id})
                    exists = sql.cursor.fetchone()[0] > 0

                    if not exists:
                        # Insert part data
                        part_name = cart_item.get('part_name', '')
                        color_name = cart_item.get('color_name', '')

                        insert_part_query = """
                            INSERT OR IGNORE INTO "rebrickable_parts" (
                                "part",
                                "name",
                                "color_id",
                                "color_name",
                                "color_rgb",
                                "color_transparent",
                                "image",
                                "url",
                                "bricklink_color_id",
                                "bricklink_color_name"
                            ) VALUES (
                                :part,
                                :name,
                                :color_id,
                                :color_name,
                                :color_rgb,
                                :color_transparent,
                                :image,
                                :url,
                                :bricklink_color_id,
                                :bricklink_color_name
                            )
                        """

                        sql.cursor.execute(insert_part_query, {
                            'part': part_num,
                            'name': part_name,
                            'color_id': color_id,
                            'color_name': color_name,
                            'color_rgb': color_info.get('rgb', ''),
                            'color_transparent': color_info.get('is_trans', False),
                            'image': color_info.get('part_img_url', ''),
                            'url': f'https://rebrickable.com/parts/{part_num}/',
                            'bricklink_color_id': color_info.get('bricklink_color_id', None),
                            'bricklink_color_name': color_info.get('bricklink_color_name', None)
                        })
                except Exception as e:
                    logger.warning(f'Could not ensure part data for {part_num}/{color_id}: {e}')

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
            logger.error(f'Error creating lot: {e}')
            return False
        except Exception as e:
            socket.fail(message=f'Unexpected error creating lot: {str(e)}')
            logger.error(f'Unexpected error creating lot: {e}')
            logger.error(traceback.format_exc())
            return False
