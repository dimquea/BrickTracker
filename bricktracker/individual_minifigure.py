import logging
import traceback
from typing import Any, Self, TYPE_CHECKING
from uuid import uuid4

from flask import current_app, url_for

from .exceptions import NotFoundException, DatabaseException, ErrorException
from .parser import parse_minifig
from .rebrickable import Rebrickable
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
    light_query: str = 'individual_minifigure/select/light'
    insert_query: str = 'individual_minifigure/insert'

    # Delete a individual minifigure
    def delete(self, /) -> None:
        BrickSQL().executescript(
            'individual_minifigure/delete/individual_minifigure',
            id=self.fields.id
        )

    # Import a individual minifigure into the database
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
        """Download minifigure parts using get_minifig_elements()"""
        try:
            # Check if we have cached parts data from load()
            if hasattr(self, '_cached_parts_response'):
                response = self._cached_parts_response
                logger.debug('Using cached parts data from load()')
            else:
                # Need to fetch parts data
                socket.auto_progress(
                    message='Minifigure {figure}: loading parts from Rebrickable'.format(
                        figure=self.fields.figure
                    ),
                    increment_total=True,
                )

                logger.debug('rebrick.lego.get_minifig_elements("{figure}")'.format(
                    figure=self.fields.figure,
                ))

                # Load parts data from Rebrickable API
                import json
                from rebrick import lego

                parameters = {
                    'api_key': current_app.config['REBRICKABLE_API_KEY'],
                    'page_size': current_app.config['REBRICKABLE_PAGE_SIZE'],
                }

                response = json.loads(lego.get_minifig_elements(
                    self.fields.figure,
                    **parameters
                ).read())

            socket.auto_progress(
                message='Minifigure {figure}: saving parts to database'.format(
                    figure=self.fields.figure
                ),
            )

            # Insert each part into individual_minifigure_parts table
            from .rebrickable_part import RebrickablePart

            if 'results' in response:
                logger.debug(f'Processing {len(response["results"])} parts for minifigure {self.fields.figure}')

                for idx, result in enumerate(response['results']):
                    part_num = result['part']['part_num']
                    color_id = result['color']['id']

                    logger.debug(
                        f'Part {idx+1}/{len(response["results"])}: {part_num} '
                        f'(color: {color_id}, quantity: {result["quantity"]})'
                    )

                    # Insert rebrickable part data first
                    part_data = RebrickablePart.from_rebrickable(result)
                    logger.debug(f'Rebrickable part data keys: {list(part_data.keys())}')

                    # Insert into rebrickable_parts if not exists
                    BrickSQL().execute(
                        'rebrickable/part/insert',
                        parameters=part_data,
                        commit=False,
                    )

                    # Download part image if not using remote images
                    if not current_app.config['USE_REMOTE_IMAGES']:
                        # Create a RebrickablePart instance for image download
                        from .set import BrickSet
                        try:
                            part_instance = RebrickablePart(record=part_data)
                            from .rebrickable_image import RebrickableImage
                            RebrickableImage(
                                BrickSet(),  # Dummy set
                                minifigure=self,
                                part=part_instance,
                            ).download()
                        except Exception as e:
                            logger.warning(
                                f'Could not download image for part {part_num}: {e}'
                            )

                    # Insert into bricktracker_individual_minifigure_parts
                    individual_part_params = {
                        'id': self.fields.id,
                        'part': part_num,
                        'color': color_id,
                        'spare': result.get('is_spare', False),
                        'quantity': result['quantity'],
                        'element': result.get('element_id'),
                        'rebrickable_inventory': result['id'],
                    }
                    logger.debug(f'Individual part params: {individual_part_params}')

                    BrickSQL().execute(
                        'individual_minifigure/part/insert',
                        parameters=individual_part_params,
                        commit=False,
                    )

                logger.debug(f'Successfully inserted all {len(response["results"])} parts')
            else:
                logger.warning(f'No results in parts response for minifigure {self.fields.figure}')

            # Clean up cached data
            if hasattr(self, '_cached_parts_response'):
                delattr(self, '_cached_parts_response')

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
        """Insert rebrickable minifigure data (without set association)"""
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
                logger.debug(f'Downloaded image for individual minifigure {self.fields.figure}')
            except Exception as e:
                logger.warning(
                    f'Could not download image for individual minifigure {self.fields.figure}: {e}'
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
                message='Minifigure {figure}: loading from Rebrickable'.format(
                    figure=figure,
                ),
            )

            logger.debug('rebrick.lego.get_minifig_elements("{figure}")'.format(
                figure=figure,
            ))

            # Load from Rebrickable using get_minifig_elements
            # This gives us both minifigure info and parts in one call
            import json
            from rebrick import lego

            parameters = {
                'api_key': current_app.config['REBRICKABLE_API_KEY'],
                'page_size': current_app.config['REBRICKABLE_PAGE_SIZE'],
            }

            response = json.loads(lego.get_minifig_elements(
                figure,
                **parameters
            ).read())

            # Extract minifigure info from the first part's metadata
            if 'results' in response and len(response['results']) > 0:
                first_part = response['results'][0]

                # Build minifigure data from the response
                self.fields.figure = first_part['set_num']
                self.fields.number_of_parts = response['count']

                # We need to fetch the proper name and image from get_minifig()
                # This is a small additional call but gives us the proper minifigure data
                try:
                    # get_minifig() only needs api_key, not page_size
                    minifig_params = {
                        'api_key': current_app.config['REBRICKABLE_API_KEY']
                    }
                    minifig_response = json.loads(lego.get_minifig(
                        figure,
                        **minifig_params
                    ).read())
                    self.fields.name = minifig_response.get('name', f"Minifigure {figure}")

                    # Use the minifig image from get_minifig() - this is the assembled minifig
                    self.fields.image = minifig_response.get('set_img_url')

                    # Extract number from figure (e.g., fig-005997 -> 5997)
                    try:
                        self.fields.number = int(figure.split('-')[1])
                    except:
                        self.fields.number = 0

                except Exception as e:
                    logger.warning(f'Could not fetch minifigure name: {e}')
                    self.fields.name = f"Minifigure {figure}"
                    # Try to extract number anyway
                    try:
                        self.fields.number = int(figure.split('-')[1])
                    except:
                        self.fields.number = 0

                    # Fallback: try to extract image from first part with element_id
                    self.fields.image = None
                    for result in response['results']:
                        if result.get('element_id') and result['part'].get('part_img_url'):
                            self.fields.image = result['part']['part_img_url']
                            break

                # Store the parts data for later use in download
                self._cached_parts_response = response
            else:
                raise NotFoundException(f'Minifigure {figure} has no parts in Rebrickable')

            socket.emit('MINIFIGURE_LOADED', self.short(
                from_download=from_download
            ))

            if not from_download:
                socket.complete(
                    message='Minifigure {figure}: loaded from Rebrickable'.format(
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
                    message='Could not load the minifigure from Rebrickable: {error}. Data: {data}'.format(
                        error=error_msg,
                        data=data,
                    )
                )

            if not isinstance(e, (NotFoundException, ErrorException)):
                logger.debug(traceback.format_exc())

        return False

    # Return a short form of the minifigure
    def short(self, /, *, from_download: bool = False) -> dict[str, Any]:
        return {
            'download': from_download,
            'image': self.url_for_image(),
            'name': self.fields.name,
            'figure': self.fields.figure,
        }

    # Select a individual minifigure by ID
    def select_by_id(self, id: str, /) -> Self:
        # Save the ID parameter
        self.fields.id = id

        # Import status list here to get metadata columns
        from .set_status_list import BrickSetStatusList

        # Pass metadata columns to the query with correct table names for individual minifigures
        context = {
            'owners': ', ' + BrickSetOwnerList.as_columns(table='bricktracker_individual_minifigure_owners') if BrickSetOwnerList.list() else '',
            'statuses': ', ' + BrickSetStatusList.as_columns(table='bricktracker_individual_minifigure_statuses', all=True) if BrickSetStatusList.list(all=True) else '',
            'tags': ', ' + BrickSetTagList.as_columns(table='bricktracker_individual_minifigure_tags') if BrickSetTagList.list() else '',
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
        """String representation for debugging"""
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
            'image': data.get('set_img_url'),
            'number_of_parts': int(data.get('num_parts', 0)),
        }
