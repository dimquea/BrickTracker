import logging
from typing import Self

from flask import current_app

from .exceptions import NotFoundException
from .parser import parse_set
from .bricklink import BrickLink
from .rebrickable_image import RebrickableImage
from .record_list import BrickRecordList
from .wish import BrickWish
from .wish_owner_list import BrickWishOwnerList

logger = logging.getLogger(__name__)


# All the wished sets from the database
class BrickWishList(BrickRecordList[BrickWish]):
    # Queries
    select_query: str = 'wish/list/all'

    # Implementation of abstract list method
    def list(self, /, *, override_query: str | None = None, **context) -> None:
        # Use provided order or default
        order = context.pop('order', current_app.config['WISHES_DEFAULT_ORDER'])

        # Load the wished sets from the database
        for record in self.select(
            override_query=override_query,
            order=order,
            owners=BrickWishOwnerList.as_columns(),
            **context
        ):
            brickwish = BrickWish(record=record)
            self.records.append(brickwish)

    # All the wished sets
    def all(self, /) -> Self:
        self.list()
        return self

    # Add a set to the wishlist
    @staticmethod
    def add(set: str, /) -> None:
        try:
            set = parse_set(set)
            BrickWish().select_specific(set)
        except NotFoundException:
            logger.debug('BrickLink catalog get_set("{set}")'.format(
                set=set,
            ))

            brickwish = BrickLink[BrickWish](
                'get_set',
                set,
                BrickWish,
            ).get()

            # Insert into database
            brickwish.insert()

            if not current_app.config['USE_REMOTE_IMAGES']:
                RebrickableImage(brickwish).download()
