import logging
from typing import Self

from flask import current_app

from .exceptions import NotFoundException
from .parser import parse_set
from .rebrickable import Rebrickable
from .rebrickable_image import RebrickableImage
from .record_list import BrickRecordList
from .wish import BrickWish

logger = logging.getLogger(__name__)


# All the wished sets from the database
class BrickWishList(BrickRecordList[BrickWish]):
    # Queries
    select_query: str = 'wish/list/all'

    # All the wished sets
    def all(self, /) -> Self:
        # Load the wished sets from the database
        for record in self.select(
            order=current_app.config['WISHES_DEFAULT_ORDER']
        ):
            brickwish = BrickWish(record=record)

            self.records.append(brickwish)

        return self

    # Add a set to the wishlist
    @staticmethod
    def add(set: str, /) -> None:
        try:
            set = parse_set(set)
            BrickWish().select_specific(set)
        except NotFoundException:
            logger.debug('rebrick.lego.get_set("{set}")'.format(
                set=set,
            ))

            brickwish = Rebrickable[BrickWish](
                'get_set',
                set,
                BrickWish,
            ).get()

            # Insert into database
            brickwish.insert()

            if not current_app.config['USE_REMOTE_IMAGES']:
                RebrickableImage(brickwish).download()
