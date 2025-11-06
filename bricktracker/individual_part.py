import logging
import os
import traceback
from typing import Any, Self, TYPE_CHECKING
from urllib.parse import urlparse
from uuid import uuid4

from flask import current_app, url_for
import requests
from shutil import copyfileobj

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
        self.fields.id = id
        if not self.select(override_query=self.select_query):
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
        """Generate HTML ID for form elements"""
        components: list[str] = ['individual-part']

        if prefix is not None:
            components.append(prefix)

        components.append(self.fields.part)
        components.append(str(self.fields.color))
        components.append(self.fields.id)

        return '-'.join(components)

    # URL for quantity update
    def url_for_quantity(self, /) -> str:
        """URL for updating quantity"""
        return url_for('individual_part.update_quantity', id=self.fields.id)

    # URL for description update
    def url_for_description(self, /) -> str:
        """URL for updating description"""
        return url_for('individual_part.update_description', id=self.fields.id)

    # URL for problem (missing/damaged) update
    def url_for_problem(self, problem_type: str, /) -> str:
        """URL for updating problem counts (missing/damaged)"""
        if problem_type == 'missing':
            return url_for('individual_part.update_missing', id=self.fields.id)
        elif problem_type == 'damaged':
            return url_for('individual_part.update_damaged', id=self.fields.id)
        else:
            raise ValueError(f'Invalid problem type: {problem_type}')

    # URL for checked status update
    def url_for_checked(self, /) -> str:
        """URL for updating checked status"""
        return url_for('individual_part.update_checked', id=self.fields.id)

    # URL for this part's detail page
    def url(self, /) -> str:
        """URL for this part's detail page"""
        return url_for('individual_part.details', id=self.fields.id)

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
        """
        Get color information from cache table, or fetch from API if not cached.
        Returns dict with: name, rgb, is_trans, bricklink_color_id, bricklink_color_name
        """
        sql = BrickSQL()

        # Check if color exists in cache
        check_query = """
            SELECT "color_id", "name", "rgb", "is_trans",
                   "bricklink_color_id", "bricklink_color_name"
            FROM "rebrickable_colors"
            WHERE "color_id" = :color_id
        """
        sql.cursor.execute(check_query, {'color_id': color_id})
        result = sql.cursor.fetchone()

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

        # Color not in cache, fetch from API
        try:
            import rebrick
            import json

            rebrick.init(current_app.config['REBRICKABLE_API_KEY'])
            color_response = rebrick.lego.get_color(color_id)
            color_data = json.loads(color_response.read())

            # Extract BrickLink color info
            bricklink_color_id = None
            bricklink_color_name = None

            if 'external_ids' in color_data and 'BrickLink' in color_data['external_ids']:
                bricklink_info = color_data['external_ids']['BrickLink']
                if 'ext_ids' in bricklink_info and bricklink_info['ext_ids']:
                    bricklink_color_id = bricklink_info['ext_ids'][0]
                if 'ext_descrs' in bricklink_info and bricklink_info['ext_descrs']:
                    bricklink_color_name = bricklink_info['ext_descrs'][0][0] if bricklink_info['ext_descrs'][0] else None

            # Store in cache
            insert_query = """
                INSERT OR REPLACE INTO "rebrickable_colors" (
                    "color_id", "name", "rgb", "is_trans",
                    "bricklink_color_id", "bricklink_color_name"
                ) VALUES (
                    :color_id, :name, :rgb, :is_trans,
                    :bricklink_color_id, :bricklink_color_name
                )
            """
            sql.cursor.execute(insert_query, {
                'color_id': color_data['id'],
                'name': color_data['name'],
                'rgb': color_data.get('rgb'),
                'is_trans': color_data.get('is_trans', False),
                'bricklink_color_id': bricklink_color_id,
                'bricklink_color_name': bricklink_color_name
            })
            sql.connection.commit()

            logger.info(f'Cached color {color_id} ({color_data["name"]}) with BrickLink ID {bricklink_color_id}')

            return {
                'color_id': color_data['id'],
                'name': color_data['name'],
                'rgb': color_data.get('rgb'),
                'is_trans': color_data.get('is_trans', False),
                'bricklink_color_id': bricklink_color_id,
                'bricklink_color_name': bricklink_color_name
            }

        except Exception as e:
            logger.warning(f'Could not fetch color {color_id} from API: {e}')
            return None

    # Download image for this part
    def download_image(self, image_url: str, /) -> None:
        if not image_url:
            return

        # Create image_id from URL
        image_id, _ = os.path.splitext(os.path.basename(urlparse(image_url).path))

        if not image_id:
            return

        # Build path
        parts_folder = current_app.config['PARTS_FOLDER']
        extension = 'jpg'  # Everything is saved as jpg
        path = os.path.join(
            current_app.static_folder,  # type: ignore
            parts_folder,
            f'{image_id}.{extension}'
        )

        # Avoid downloading if file exists
        if os.path.exists(path):
            return

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(path), exist_ok=True)

        # Download the image
        try:
            response = requests.get(image_url, stream=True)
            if response.ok:
                with open(path, 'wb') as f:
                    copyfileobj(response.raw, f)
                logger.info(f'Downloaded image for part {self.fields.part} color {self.fields.color} to {path}')
        except Exception as e:
            logger.warning(f'Could not download image for part {self.fields.part} color {self.fields.color}: {e}')

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

            # Fetch available colors from Rebrickable
            import rebrick
            import json

            rebrick.init(current_app.config['REBRICKABLE_API_KEY'])

            # Setup progress tracking
            socket.progress_count = 0
            socket.progress_total = 2  # Fetch part info + fetch colors

            try:
                # Get part information for the name
                socket.auto_progress(message='Fetching part information')
                part_response = rebrick.lego.get_part(part_num)
                part_data = json.loads(part_response.read())
                part_name = part_data.get('name', part_num)

                # Get all available colors for this part
                socket.auto_progress(message='Fetching available colors')
                colors_response = rebrick.lego.get_part_colors(part_num)
                colors_data = json.loads(colors_response.read())

                # Extract the results
                colors = colors_data.get('results', [])

                if not colors:
                    raise ErrorException(f'No colors found for part {part_num}')

                # Download images locally if USE_REMOTE_IMAGES is False
                if not current_app.config.get('USE_REMOTE_IMAGES', False):
                    # Add image downloads to progress
                    socket.progress_total += len(colors)

                    for color in colors:
                        image_url = color.get('part_img_url', '')
                        if image_url:
                            socket.auto_progress(message=f'Downloading image for {color.get("color_name", "color")}')
                            try:
                                self.download_image(image_url)
                            except Exception as e:
                                logger.warning(f'Could not download image for part {part_num} color {color.get("color_id")}: {e}')

                # Emit the part colors loaded event
                logger.info(f'Emitting {len(colors)} colors for part {part_num} ({part_name})')

                socket.emit(
                    'PART_COLORS_LOADED',
                    {
                        'part': part_num,
                        'part_name': part_name,
                        'colors': colors,
                        'count': len(colors)
                    }
                )

                logger.info(f'Successfully loaded {len(colors)} colors for part {part_num}')
                return True

            except Exception as e:
                error_msg = str(e)

                # Provide helpful error message for printed/decorated parts
                if '404' in error_msg or 'Not Found' in error_msg:
                    # Check if this might be a printed part (has letters/pattern code)
                    base_part = ''.join(c for c in part_num if c.isdigit())

                    if base_part and base_part != part_num:
                        raise ErrorException(
                            f'Part {part_num} not found in Rebrickable. This appears to be a printed/decorated part. '
                            f'Try searching for the base part number: {base_part}'
                        )
                    else:
                        raise ErrorException(
                            f'Part {part_num} not found in Rebrickable. '
                            f'Please verify the part number is correct.'
                        )
                else:
                    raise ErrorException(
                        f'Could not fetch colors for part {part_num}: {error_msg}'
                    )

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
            color_id = int(data.get('color', 0))
            quantity = int(data.get('quantity', 1))

            if not part_num:
                raise ErrorException('Part number is required')
            if color_id <= 0:
                raise ErrorException('Valid color ID is required')
            if quantity <= 0:
                raise ErrorException('Quantity must be greater than 0')

            # Check if color info was pre-loaded (from load_colors)
            color_data = data.get('color_info', None)
            part_name = data.get('part_name', None)

            # Validate part+color exists in rebrickable_parts
            # If not, fetch from Rebrickable or use pre-loaded data and insert
            sql = BrickSQL()
            check_query = """
                SELECT COUNT(*) FROM "rebrickable_parts"
                WHERE "part" = :part AND "color_id" = :color_id
            """
            sql.cursor.execute(check_query, {'part': part_num, 'color_id': color_id})
            exists = sql.cursor.fetchone()[0] > 0

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

                    # Insert into rebrickable_parts using the pre-loaded data
                    insert_part_query = """
                        INSERT OR IGNORE INTO "rebrickable_parts" (
                            "part", "color_id", "color_name", "color_rgb", "color_transparent",
                            "bricklink_color_id", "bricklink_color_name",
                            "name", "image", "url"
                        ) VALUES (
                            :part, :color_id, :color_name, :color_rgb, :color_transparent,
                            :bricklink_color_id, :bricklink_color_name,
                            :name, :image, :url
                        )
                    """
                    sql.cursor.execute(insert_part_query, {
                        'part': part_num,
                        'color_id': color_id,
                        'color_name': color_data.get('color_name', ''),
                        'color_rgb': full_color_info.get('rgb') if full_color_info else None,
                        'color_transparent': full_color_info.get('is_trans') if full_color_info else None,
                        'bricklink_color_id': full_color_info.get('bricklink_color_id') if full_color_info else None,
                        'bricklink_color_name': full_color_info.get('bricklink_color_name') if full_color_info else None,
                        'name': part_name,
                        'image': image_url,
                        'url': f'https://rebrickable.com/parts/{part_num}/'
                    })
                else:
                    # Fetch from Rebrickable (fallback for old workflow)
                    socket.auto_progress(message='Fetching part info from Rebrickable')
                    import rebrick
                    import json

                    # Initialize rebrick with API key
                    rebrick.init(current_app.config['REBRICKABLE_API_KEY'])

                    try:
                        # Get part information
                        part_info = json.loads(rebrick.lego.get_part(part_num).read())

                        # Get color information (this also caches it in rebrickable_colors)
                        # full_color_info already fetched above, but get again to be sure
                        if not full_color_info:
                            full_color_info = IndividualPart.get_or_fetch_color(color_id)

                        # Get part+color specific info (for the image)
                        part_color_info = json.loads(rebrick.lego.get_part_color(part_num, color_id).read())

                        # Get image URL
                        image_url = part_color_info.get('part_img_url', part_info.get('part_img_url', ''))

                        # Insert into rebrickable_parts with BrickLink color info
                        insert_part_query = """
                            INSERT OR IGNORE INTO "rebrickable_parts" (
                                "part", "color_id", "color_name", "color_rgb", "color_transparent",
                                "bricklink_color_id", "bricklink_color_name",
                                "name", "image", "url"
                            ) VALUES (
                                :part, :color_id, :color_name, :color_rgb, :color_transparent,
                                :bricklink_color_id, :bricklink_color_name,
                                :name, :image, :url
                            )
                        """
                        sql.cursor.execute(insert_part_query, {
                            'part': part_info['part_num'],
                            'color_id': full_color_info['color_id'] if full_color_info else color_id,
                            'color_name': full_color_info['name'] if full_color_info else '',
                            'color_rgb': full_color_info['rgb'] if full_color_info else None,
                            'color_transparent': full_color_info['is_trans'] if full_color_info else None,
                            'bricklink_color_id': full_color_info.get('bricklink_color_id') if full_color_info else None,
                            'bricklink_color_name': full_color_info.get('bricklink_color_name') if full_color_info else None,
                            'name': part_info['name'],
                            'image': image_url,
                            'url': part_info['part_url']
                        })

                    except Exception as e:
                        error_msg = str(e)

                        # Provide helpful error message for printed/decorated parts
                        if '404' in error_msg or 'Not Found' in error_msg:
                            base_part = ''.join(c for c in part_num if c.isdigit())

                            if base_part and base_part != part_num:
                                raise ErrorException(
                                    f'Part {part_num} with color {color_id} not found in Rebrickable. '
                                    f'This appears to be a printed/decorated part. '
                                    f'Try using the base part number: {base_part}'
                                )
                            else:
                                raise ErrorException(
                                    f'Part {part_num} with color {color_id} not found in Rebrickable. '
                                    f'Please verify the part number is correct.'
                                )
                        else:
                            raise ErrorException(
                                f'Part {part_num} with color {color_id} not found in Rebrickable: {error_msg}'
                            )
            else:
                # Part already exists in rebrickable_parts, get the image URL
                sql.cursor.execute(
                    'SELECT "image" FROM "rebrickable_parts" WHERE "part" = :part AND "color_id" = :color_id',
                    {'part': part_num, 'color_id': color_id}
                )
                result = sql.cursor.fetchone()
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
                    logger.warning(f'Could not download image for part {part_num} color {color_id}: {e}')

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

    # Update a field
    def update_field(self, field: str, value: Any, /) -> Self:
        setattr(self.fields, field, value)

        # Use a specific update query for each field
        sql = BrickSQL()
        update_query = f"""
            UPDATE "bricktracker_individual_parts"
            SET "{field}" = :value
            WHERE "id" = :id
        """
        sql.cursor.execute(update_query, {
            'id': self.fields.id,
            'value': value
        })
        sql.commit()

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

    # URL methods
    def url(self, /) -> str:
        return url_for('individual_part.details', id=self.fields.id)

    def url_for_quantity(self, /) -> str:
        return url_for('individual_part.update_quantity', id=self.fields.id)

    def url_for_description(self, /) -> str:
        return url_for('individual_part.update_description', id=self.fields.id)

    def url_for_problem(self, problem: str, /) -> str:
        if problem == 'missing':
            return url_for('individual_part.update_missing', id=self.fields.id)
        elif problem == 'damaged':
            return url_for('individual_part.update_damaged', id=self.fields.id)
        return ''

    def url_for_checked(self, /) -> str:
        return url_for('individual_part.update_checked', id=self.fields.id)

    def url_for_delete(self, /) -> str:
        return url_for('individual_part.delete_part', id=self.fields.id)

    def url_for_image(self, /) -> str:
        # Check if we should use remote images
        if current_app.config.get('USE_REMOTE_IMAGES', False):
            # Return remote URL directly
            if hasattr(self.fields, 'image') and self.fields.image:
                return self.fields.image
            else:
                return current_app.config.get('REBRICKABLE_IMAGE_NIL', '')
        else:
            # Use local images
            from .rebrickable_image import RebrickableImage

            if hasattr(self.fields, 'image') and self.fields.image:
                # Extract image_id from URL
                image_id, _ = os.path.splitext(os.path.basename(urlparse(self.fields.image).path))

                if image_id:
                    # Return local static URL using RebrickableImage helper
                    return RebrickableImage.static_url(image_id, 'PARTS_FOLDER')

            # Fallback to nil image
            return RebrickableImage.static_url(RebrickableImage.nil_name(), 'PARTS_FOLDER')
