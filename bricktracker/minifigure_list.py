import logging
import traceback
from typing import Any, Self, TYPE_CHECKING

from flask import current_app

from .minifigure import BrickMinifigure
from .bricklink import BrickLink
from .record_list import BrickRecordList
if TYPE_CHECKING:
    from .set import BrickSet
    from .socket import BrickSocket

logger = logging.getLogger(__name__)


# Lego minifigures
class BrickMinifigureList(BrickRecordList[BrickMinifigure]):
    brickset: 'BrickSet | None'
    order: str

    # Queries
    all_query: str = 'minifigure/list/all_unified'
    all_by_owner_query: str = 'minifigure/list/all_by_owner_unified'
    damaged_part_query: str = 'minifigure/list/damaged_part'
    last_query: str = 'minifigure/list/last'
    missing_part_query: str = 'minifigure/list/missing_part'
    problem_query: str = 'minifigure/list/problem'
    select_query: str = 'minifigure/list/from_set'
    using_part_query: str = 'minifigure/list/using_part'

    def __init__(self, /):
        super().__init__()

        # Placeholders
        self.brickset = None

        # Store the order for this list
        self.order = current_app.config['MINIFIGURES_DEFAULT_ORDER']

    # Load all minifigures
    def all(self, /) -> Self:
        self.list(override_query=self.all_query)

        return self

    # Load all minifigures with problems filter
    def all_filtered(self, /, owner_id: str | None = None, problems_filter: str = 'all', theme_id: str = 'all', year: str = 'all', individuals_filter: str = 'all') -> Self:
        # Save the owner_id parameter
        if owner_id is not None:
            self.fields.owner_id = owner_id

        context = {}
        if problems_filter and problems_filter != 'all':
            context['problems_filter'] = problems_filter
        if theme_id and theme_id != 'all':
            context['theme_id'] = theme_id
        if year and year != 'all':
            context['year'] = year
        if individuals_filter and individuals_filter != 'all':
            context['individuals_filter'] = individuals_filter

        # Choose query based on whether owner filtering is needed
        if owner_id and owner_id != 'all':
            query = self.all_by_owner_query
        else:
            query = self.all_query

        self.list(override_query=query, **context)
        return self

    # Load all minifigures by owner
    def all_by_owner(self, owner_id: str | None = None, /) -> Self:
        # Save the owner_id parameter
        self.fields.owner_id = owner_id

        # Load the minifigures from the database
        self.list(override_query=self.all_by_owner_query)

        return self

    # Load all minifigures by owner with problems filter
    def all_by_owner_filtered(self, /, owner_id: str | None = None, problems_filter: str = 'all', theme_id: str = 'all', year: str = 'all', individuals_filter: str = 'all') -> Self:
        # Save the owner_id parameter
        self.fields.owner_id = owner_id

        context = {}
        if problems_filter and problems_filter != 'all':
            context['problems_filter'] = problems_filter
        if theme_id and theme_id != 'all':
            context['theme_id'] = theme_id
        if year and year != 'all':
            context['year'] = year
        if individuals_filter and individuals_filter != 'all':
            context['individuals_filter'] = individuals_filter

        # Load the minifigures from the database
        self.list(override_query=self.all_by_owner_query, **context)

        return self

    # Load minifigures with pagination support
    def all_filtered_paginated(
        self,
        owner_id: str | None = None,
        problems_filter: str = 'all',
        theme_id: str = 'all',
        year: str = 'all',
        individuals_filter: str = 'all',
        search_query: str | None = None,
        page: int = 1,
        per_page: int = 50,
        sort_field: str | None = None,
        sort_order: str = 'asc'
    ) -> tuple[Self, int]:
        # Prepare filter context
        filter_context = {}
        if owner_id and owner_id != 'all':
            filter_context['owner_id'] = owner_id
            list_query = self.all_by_owner_query
        else:
            list_query = self.all_query

        if search_query:
            filter_context['search_query'] = search_query

        if problems_filter and problems_filter != 'all':
            filter_context['problems_filter'] = problems_filter

        if theme_id and theme_id != 'all':
            filter_context['theme_id'] = theme_id

        if year and year != 'all':
            filter_context['year'] = year

        if individuals_filter and individuals_filter != 'all':
            filter_context['individuals_filter'] = individuals_filter

        # Field mapping for sorting (using column names from the unified query)
        field_mapping = {
            'name': '"name"',
            'parts': '"number_of_parts"',
            'quantity': '"total_quantity"',
            'missing': '"total_missing"',
            'damaged': '"total_damaged"',
            'sets': '"total_sets"'
        }

        # Use the base pagination method
        return self.paginate(
            page=page,
            per_page=per_page,
            sort_field=sort_field,
            sort_order=sort_order,
            list_query=list_query,
            field_mapping=field_mapping,
            **filter_context
        )

    # Minifigures with a part damaged part
    def damaged_part(self, part: str, color: int, /) -> Self:
        # Save the parameters to the fields
        self.fields.part = part
        self.fields.color = color

        # Load the minifigures from the database
        self.list(override_query=self.damaged_part_query)

        return self

    # Last added minifigure
    def last(self, /, *, limit: int = 6) -> Self:
        # Randomize
        if current_app.config['RANDOM']:
            order = 'RANDOM()'
        else:
            order = '"bricktracker_minifigures"."rowid" DESC'

        self.list(override_query=self.last_query, order=order, limit=limit)

        return self

    # Base minifigure list
    def list(
        self,
        /,
        *,
        override_query: str | None = None,
        order: str | None = None,
        limit: int | None = None,
        **context: Any,
    ) -> None:
        if order is None:
            order = self.order

        if hasattr(self, 'brickset'):
            brickset = self.brickset
        else:
            brickset = None

        # Prepare template context for owner filtering
        context_vars = {}
        if hasattr(self.fields, 'owner_id') and self.fields.owner_id is not None:
            context_vars['owner_id'] = self.fields.owner_id

        # Merge with any additional context passed in
        context_vars.update(context)

        # Load the sets from the database
        for record in super().select(
            override_query=override_query,
            order=order,
            limit=limit,
            **context_vars
        ):
            minifigure = BrickMinifigure(brickset=brickset, record=record)

            self.records.append(minifigure)

    # Load minifigures from a brickset
    def from_set(self, brickset: 'BrickSet', /) -> Self:
        # Save the brickset
        self.brickset = brickset

        # Load the minifigures from the database
        self.list()

        return self

    # Minifigures missing a part
    def missing_part(self, part: str, color: int, /) -> Self:
        # Save the parameters to the fields
        self.fields.part = part
        self.fields.color = color

        # Load the minifigures from the database
        self.list(override_query=self.missing_part_query)

        return self

    # Minifigures marked as missing or damaged
    #
    # Строка на пару набор-фигурка: отметка стоит именно на паре, и
    # странице проблем важно, в каком наборе фигурки не хватает.
    def problem(self, /) -> Self:
        self.list(
            override_query=self.problem_query,
            order='"bricktracker_sets"."set" ASC, "rebrickable_minifigures"."name" ASC',  # noqa: E501
        )

        return self

    # Minifigure using a part
    def using_part(self, part: str, color: int, /) -> Self:
        # Save the parameters to the fields
        self.fields.part = part
        self.fields.color = color

        # Load the minifigures from the database
        self.list(override_query=self.using_part_query)

        return self

    # Return a dict with common SQL parameters for a minifigures list
    def sql_parameters(self, /) -> dict[str, Any]:
        parameters: dict[str, Any] = super().sql_parameters()

        if self.brickset is not None:
            parameters['id'] = self.brickset.fields.id

        # Add owner_id parameter for owner filtering
        if hasattr(self.fields, 'owner_id') and self.fields.owner_id is not None:
            parameters['owner_id'] = self.fields.owner_id

        return parameters

    # Import the minifigures from Rebrickable
    @staticmethod
    def download(
        socket: 'BrickSocket',
        brickset: 'BrickSet',
        /,
        *,
        refresh: bool = False
    ) -> bool:
        try:
            socket.auto_progress(
                message='Set {set}: loading minifigures from the BrickLink catalog'.format(  # noqa: E501
                    set=brickset.fields.set,
                ),
                increment_total=True,
            )

            logger.debug('BrickLink catalog get_set_minifigs("{set}")'.format(  # noqa: E501
                set=brickset.fields.set,
            ))

            minifigures = BrickLink[BrickMinifigure](
                'get_set_minifigs',
                brickset.fields.set,
                BrickMinifigure,
                socket=socket,
                brickset=brickset,
            ).list()

            # Process each minifigure
            for minifigure in minifigures:
                if not minifigure.download(socket, refresh=refresh):
                    return False

            return True

        except Exception as e:
            socket.fail(
                message='Error while importing set {set} minifigure list: {error}'.format(  # noqa: E501
                    set=brickset.fields.set,
                    error=e,
                )
            )

            logger.debug(traceback.format_exc())

            return False
