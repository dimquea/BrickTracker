from datetime import datetime
import logging
import traceback
from typing import Any, Self, TYPE_CHECKING
from uuid import uuid4

from flask import current_app, url_for

from .exceptions import NotFoundException, DatabaseException, ErrorException
from .minifigure_list import BrickMinifigureList
from .part_list import BrickPartList
from .rebrickable_set import RebrickableSet
from .set_owner_list import BrickSetOwnerList
from .set_purchase_location_list import BrickSetPurchaseLocationList
from .set_status_list import BrickSetStatusList
from .set_storage_list import BrickSetStorageList
from .set_tag_list import BrickSetTagList
from .sql import BrickSQL
if TYPE_CHECKING:
    from .socket import BrickSocket

logger = logging.getLogger(__name__)


# Lego brick set
class BrickSet(RebrickableSet):
    # Queries
    select_query: str = 'set/select/full'
    light_query: str = 'set/select/light'
    insert_query: str = 'set/insert'
    update_purchase_date_query: str = 'set/update/purchase_date'
    update_purchase_price_query: str = 'set/update/purchase_price'

    # Delete a set
    def delete(self, /) -> None:
        BrickSQL().executescript(
            'set/delete/set',
            id=self.fields.id
        )

    # Import a set into the database
    def download(self, socket: 'BrickSocket', data: dict[str, Any], /) -> bool:
        # Load the set
        if not self.load(socket, data, from_download=True):
            return False

        try:
            # Insert into the database
            socket.auto_progress(
                message='Set {set}: inserting into database'.format(
                    set=self.fields.set
                ),
                increment_total=True,
            )

            # Grabbing the refresh flag
            refresh: bool = bool(data.get('refresh', False))

            # Generate an UUID for self
            self.fields.id = str(uuid4())

            # Insert the rebrickable set into database FIRST
            # This must happen before inserting bricktracker_sets due to FK constraint
            self.insert_rebrickable()

            if not refresh:
                # Save the storage
                storage = BrickSetStorageList.get(
                    data.get('storage', ''),
                    allow_none=True
                )
                self.fields.storage = storage.fields.id

                # Save the purchase location
                purchase_location = BrickSetPurchaseLocationList.get(
                    data.get('purchase_location', ''),
                    allow_none=True
                )
                self.fields.purchase_location = purchase_location.fields.id

                # Insert into database (deferred - will execute at final commit)
                # All operations are atomic - if anything fails, nothing is committed
                self.insert(commit=False)

                # Save the owners (deferred - will execute at final commit)
                owners: list[str] = list(data.get('owners', []))

                for id in owners:
                    owner = BrickSetOwnerList.get(id)
                    owner.update_set_state(self, state=True, commit=False)

                # Save the tags (deferred - will execute at final commit)
                tags: list[str] = list(data.get('tags', []))

                for id in tags:
                    tag = BrickSetTagList.get(id)
                    tag.update_set_state(self, state=True, commit=False)

            # Load the inventory
            if not BrickPartList.download(socket, self, refresh=refresh):
                return False

            # Load the minifigures
            if not BrickMinifigureList.download(socket, self, refresh=refresh):
                return False

            # Commit the transaction to the database
            socket.auto_progress(
                message='Set {set}: writing to the database'.format(
                    set=self.fields.set
                ),
                increment_total=True,
            )

            BrickSQL().commit()

            if refresh:
                # Info
                logger.info('Set {set}: imported (id: {id})'.format(
                    set=self.fields.set,
                    id=self.fields.id,
                ))

                # Complete
                socket.complete(
                    message='Set {set}: refreshed'.format(  # noqa: E501
                        set=self.fields.set,
                    ),
                    download=True
                )
            else:
                # Info
                logger.info('Set {set}: refreshed'.format(
                    set=self.fields.set,
                ))

                # Complete
                socket.complete(
                    message='Set {set}: imported (<a href="{url}">Go to the set</a>)'.format(  # noqa: E501
                        set=self.fields.set,
                        url=self.url()
                    ),
                    download=True
                )

        except Exception as e:
            socket.fail(
                message='Error while importing set {set}: {error}'.format(
                    set=self.fields.set,
                    error=e,
                )
            )

            logger.debug(traceback.format_exc())

            return False

        return True

    # Purchase date
    def purchase_date(self, /, *, standard: bool = False) -> str:
        if self.fields.purchase_date is not None:
            time = datetime.fromtimestamp(self.fields.purchase_date)

            if standard:
                return time.strftime('%Y/%m/%d')
            else:
                return time.strftime(
                    current_app.config['PURCHASE_DATE_FORMAT']
                )
        else:
            return ''

    # Purchase date max formatted for consolidated sets
    def purchase_date_max_formatted(self, /, *, standard: bool = False) -> str:
        if hasattr(self.fields, 'purchase_date_max') and self.fields.purchase_date_max is not None:
            time = datetime.fromtimestamp(self.fields.purchase_date_max)

            if standard:
                return time.strftime('%Y/%m/%d')
            else:
                return time.strftime(
                    current_app.config['PURCHASE_DATE_FORMAT']
                )
        else:
            return ''

    # Purchase price with currency
    def purchase_price(self, /) -> str:
        if self.fields.purchase_price is not None:
            return '{price}{currency}'.format(
                price=self.fields.purchase_price,
                currency=current_app.config['PURCHASE_CURRENCY']
            )
        else:
            return ''

    # Minifigures
    def minifigures(self, /) -> BrickMinifigureList:
        return BrickMinifigureList().from_set(self)

    # Parts
    def parts(self, /) -> BrickPartList:
        return BrickPartList().list_specific(self)

    # Select a light set (with an id)
    def select_light(self, id: str, /) -> Self:
        # Save the parameters to the fields
        self.fields.id = id

        # Load from database
        if not self.select(override_query=self.light_query):
            raise NotFoundException(
                'Set with ID {id} was not found in the database'.format(
                    id=self.fields.id,
                ),
            )

        return self

    # Select a specific set (with an id)
    def select_specific(self, id: str, /) -> Self:
        # Save the parameters to the fields
        self.fields.id = id

        # Load from database
        if not self.select(
            owners=BrickSetOwnerList.as_columns(),
            statuses=BrickSetStatusList.as_columns(all=True),
            tags=BrickSetTagList.as_columns(),
        ):
            raise NotFoundException(
                'Set with ID {id} was not found in the database'.format(
                    id=self.fields.id,
                ),
            )

        return self

    # Update the purchase date
    def update_purchase_date(self, json: Any | None, /) -> Any:
        value = json.get('value', None)  # type: ignore

        try:
            if value == '':
                value = None

            if value is not None:
                value = datetime.strptime(value, '%Y/%m/%d').timestamp()
        except Exception:
            raise ErrorException('{value} is not a date'.format(
                value=value,
            ))

        self.fields.purchase_date = value

        rows, _ = BrickSQL().execute_and_commit(
            self.update_purchase_date_query,
            parameters=self.sql_parameters()
        )

        if rows != 1:
            raise DatabaseException('Could not update the purchase date for set {set} ({id})'.format(  # noqa: E501
                set=self.fields.set,
                id=self.fields.id,
            ))

        # Info
        logger.info('Purchase date changed to "{value}" for set {set} ({id})'.format(  # noqa: E501
            value=value,
            set=self.fields.set,
            id=self.fields.id,
        ))

        return value

    # Update the purchase price
    def update_purchase_price(self, json: Any | None, /) -> Any:
        value = json.get('value', None)  # type: ignore

        try:
            if value == '':
                value = None

            if value is not None:
                value = float(value)
        except Exception:
            raise ErrorException('{value} is not a number or empty'.format(
                value=value,
            ))

        self.fields.purchase_price = value

        rows, _ = BrickSQL().execute_and_commit(
            self.update_purchase_price_query,
            parameters=self.sql_parameters()
        )

        if rows != 1:
            raise DatabaseException('Could not update the purchase price for set {set} ({id})'.format(  # noqa: E501
                set=self.fields.set,
                id=self.fields.id,
            ))

        # Info
        logger.info('Purchase price changed to "{value}" for set {set} ({id})'.format(  # noqa: E501
            value=value,
            set=self.fields.set,
            id=self.fields.id,
        ))

        return value

    # Self url
    def url(self, /) -> str:
        return url_for('set.details', id=self.fields.id)

    # Deletion url
    def url_for_delete(self, /) -> str:
        return url_for('set.delete', id=self.fields.id)

    # Actual deletion url
    def url_for_do_delete(self, /) -> str:
        return url_for('set.do_delete', id=self.fields.id)

    # Compute the url for the set instructions
    def url_for_instructions(self, /) -> str:
        if (
            not current_app.config['HIDE_SET_INSTRUCTIONS'] and
            len(self.instructions)
        ):
            return url_for(
                'set.details',
                id=self.fields.id,
                open_instructions=True
            )
        else:
            return ''

    # Compute the url for the refresh button
    def url_for_refresh(self, /) -> str:
        return url_for('set.refresh', id=self.fields.id)

    # Compute the url for the set storage
    def url_for_storage(self, /) -> str:
        if self.fields.storage is not None:
            return url_for('storage.details', id=self.fields.storage)
        else:
            return ''

    # Update purchase date url
    def url_for_purchase_date(self, /) -> str:
        return url_for('set.update_purchase_date', id=self.fields.id)

    # Update purchase price url
    def url_for_purchase_price(self, /) -> str:
        return url_for('set.update_purchase_price', id=self.fields.id)
