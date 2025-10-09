import logging
from typing import Self

from .individual_minifigure import IndividualMinifigure
from .record_list import BrickRecordList

logger = logging.getLogger(__name__)


# Individual minifigures list
class IndividualMinifigureList(BrickRecordList[IndividualMinifigure]):
    # Queries
    instances_by_figure_query: str = 'individual_minifigure/select/instances_by_figure'

    def __init__(self, /):
        super().__init__()

    # Load all individual instances of a specific minifigure figure
    def instances_by_figure(self, figure: str, /) -> Self:
        # Save the figure parameter
        self.fields.figure = figure

        # Load the instances from the database
        self.list(override_query=self.instances_by_figure_query)

        return self

    # Base individual minifigure list
    def list(
        self,
        /,
        *,
        override_query: str | None = None,
        order: str | None = None,
        limit: int | None = None,
    ) -> None:
        # Load the individual minifigures from the database
        for record in super().select(
            override_query=override_query,
            order=order,
            limit=limit,
        ):
            individual_minifigure = IndividualMinifigure(record=record)
            self.records.append(individual_minifigure)
