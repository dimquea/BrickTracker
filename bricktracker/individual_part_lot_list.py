import logging
from typing import Self, TYPE_CHECKING

from .record_list import BrickRecordList
from .individual_part_lot import IndividualPartLot

if TYPE_CHECKING:
    from .set_storage import BrickSetStorage

logger = logging.getLogger(__name__)


# List of individual part lots
class IndividualPartLotList(BrickRecordList):
    # Queries
    list_query: str = 'individual_part_lot/list/all'

    # Get all individual part lots
    def all(self, /) -> Self:
        self.list(override_query=self.list_query)
        return self

    # Base individual part lot list
    def list(
        self,
        /,
        *,
        override_query: str | None = None,
        order: str | None = None,
        limit: int | None = None,
        **context,
    ) -> None:
        # Load the individual part lots from the database
        for record in super().select(
            override_query=override_query,
            order=order,
            limit=limit,
            **context
        ):
            lot = IndividualPartLot(record=record)
            self.records.append(lot)

    # Set the record class
    def set_record_class(self, /) -> None:
        self.record_class = IndividualPartLot
