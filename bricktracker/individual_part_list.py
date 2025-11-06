import logging
from typing import Self, TYPE_CHECKING

from .record_list import BrickRecordList
from .individual_part import IndividualPart

if TYPE_CHECKING:
    from .set_storage import BrickSetStorage

logger = logging.getLogger(__name__)


# List of individual parts
class IndividualPartList(BrickRecordList):
    # Queries
    list_query: str = 'individual_part/list/all'
    by_part_query: str = 'individual_part/list/by_part'
    by_color_query: str = 'individual_part/list/by_color'
    by_part_and_color_query: str = 'individual_part/list/by_part_and_color'
    by_storage_query: str = 'individual_part/list/by_storage'
    using_storage_query: str = 'individual_part/list/using_storage'
    without_storage_query: str = 'individual_part/list/without_storage'
    problem_query: str = 'individual_part/list/problem'

    # Get all individual parts
    def all(self, /) -> Self:
        self.list(override_query=self.list_query)
        return self

    # Get individual parts by part number
    def by_part(self, part: str, /) -> Self:
        self.fields.part = part
        self.list(override_query=self.by_part_query)
        return self

    # Get individual parts by color
    def by_color(self, color_id: int, /) -> Self:
        self.fields.color = color_id
        self.list(override_query=self.by_color_query)
        return self

    # Get individual parts by part number and color
    def by_part_and_color(self, part: str, color_id: int, /) -> Self:
        self.fields.part = part
        self.fields.color = color_id
        self.list(override_query=self.by_part_and_color_query)
        return self

    # Get individual parts by storage location
    def by_storage(self, storage: 'BrickSetStorage', /) -> Self:
        self.fields.storage = storage.fields.id
        self.list(override_query=self.by_storage_query)
        return self

    # Get individual parts using a specific storage location
    def using_storage(self, storage: 'BrickSetStorage', /) -> Self:
        self.fields.storage = storage.fields.id
        self.list(override_query=self.using_storage_query)
        return self

    # Get individual parts without storage
    def without_storage(self, /) -> Self:
        self.list(override_query=self.without_storage_query)
        return self

    # Get individual parts with problems (missing or damaged)
    def with_problems(self, /) -> Self:
        self.list(override_query=self.problem_query)
        return self

    # Base individual part list
    def list(
        self,
        /,
        *,
        override_query: str | None = None,
        order: str | None = None,
        limit: int | None = None,
        **context,
    ) -> None:
        # Load the individual parts from the database
        for record in super().select(
            override_query=override_query,
            order=order,
            limit=limit,
            **context
        ):
            individual_part = IndividualPart(record=record)
            self.records.append(individual_part)

    # Set the record class
    def set_record_class(self, /) -> None:
        self.record_class = IndividualPart
