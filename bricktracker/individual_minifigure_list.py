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

        # Import metadata lists to get columns
        from .set_owner_list import BrickSetOwnerList
        from .set_status_list import BrickSetStatusList
        from .set_tag_list import BrickSetTagList

        # Prepare context with metadata columns
        context = {
            'owners': BrickSetOwnerList.as_columns(table='bricktracker_individual_minifigure_owners') if BrickSetOwnerList.list() else 'NULL AS "no_owners"',
            'statuses': BrickSetStatusList.as_columns(table='bricktracker_individual_minifigure_statuses', all=True) if BrickSetStatusList.list(all=True) else 'NULL AS "no_statuses"',
            'tags': BrickSetTagList.as_columns(table='bricktracker_individual_minifigure_tags') if BrickSetTagList.list() else 'NULL AS "no_tags"',
        }

        # Load the instances from the database
        self.list(override_query=self.instances_by_figure_query, **context)

        return self

    # Base individual minifigure list
    def list(
        self,
        /,
        *,
        override_query: str | None = None,
        order: str | None = None,
        limit: int | None = None,
        **context,
    ) -> None:
        # Load the individual minifigures from the database
        for record in super().select(
            override_query=override_query,
            order=order,
            limit=limit,
            **context
        ):
            individual_minifigure = IndividualMinifigure(record=record)
            self.records.append(individual_minifigure)
