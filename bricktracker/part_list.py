import logging
from typing import Any, Self, TYPE_CHECKING
import traceback

from flask import current_app

from .part import BrickPart
from .bricklink import BrickLink
from .record_list import BrickRecordList
if TYPE_CHECKING:
    from .minifigure import BrickMinifigure
    from .set import BrickSet
    from .socket import BrickSocket

logger = logging.getLogger(__name__)


# Lego set or minifig parts
class BrickPartList(BrickRecordList[BrickPart]):
    brickset: 'BrickSet | None'
    minifigure: 'BrickMinifigure | None'
    individual_minifigure: 'IndividualMinifigure | None'
    order: str

    # Queries
    all_query: str = 'part/list/all'
    all_by_owner_query: str = 'part/list/all_by_owner'
    different_color_query = 'part/list/with_different_color'
    last_query: str = 'part/list/last'
    minifigure_query: str = 'part/list/from_minifigure'
    problem_query: str = 'part/list/problem'
    print_query: str = 'part/list/from_print'
    select_query: str = 'part/list/specific'

    def __init__(self, /):
        super().__init__()

        # Placeholders
        self.brickset = None
        self.minifigure = None

        # Store the order for this list
        self.order = current_app.config['PARTS_DEFAULT_ORDER']

    # Load all parts
    def all(self, /) -> Self:
        self.list(override_query=self.all_query)

        return self

    # Load all parts by owner
    def all_by_owner(self, owner_id: str | None = None, /) -> Self:
        # Save the owner_id parameter
        self.fields.owner_id = owner_id

        # Load the parts from the database
        self.list(override_query=self.all_by_owner_query)

        return self

    # Load all parts with filters (owner, color, theme, year, individuals)
    def all_filtered(self, owner_id: str | None = None, color_id: str | None = None, theme_id: str | None = None, year: str | None = None, individuals_filter: str | None = None, /) -> Self:
        # Save the filter parameters
        if owner_id is not None:
            self.fields.owner_id = owner_id
        if color_id is not None:
            self.fields.color_id = color_id

        # Choose query based on whether owner filtering is needed
        if owner_id and owner_id != 'all':
            query = self.all_by_owner_query
        else:
            query = self.all_query

        # Prepare context for query
        context = {}
        # Hide spare parts from display if configured
        if current_app.config.get('HIDE_SPARE_PARTS', False):
            context['skip_spare_parts'] = True
        if theme_id and theme_id != 'all':
            context['theme_id'] = theme_id
        if year and year != 'all':
            context['year'] = year
        if individuals_filter and individuals_filter == 'only':
            context['individuals_filter'] = True

        # Load the parts from the database
        self.list(override_query=query, **context)

        return self

    # Load parts with pagination support
    def all_filtered_paginated(
        self,
        owner_id: str | None = None,
        color_id: str | None = None,
        theme_id: str | None = None,
        year: str | None = None,
        individuals_filter: str | None = None,
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

        if color_id and color_id != 'all':
            filter_context['color_id'] = color_id
        if theme_id and theme_id != 'all':
            filter_context['theme_id'] = theme_id
        if year and year != 'all':
            filter_context['year'] = year
        if individuals_filter and individuals_filter == 'only':
            filter_context['individuals_filter'] = True
        if search_query:
            filter_context['search_query'] = search_query
        # Hide spare parts from display if configured
        if current_app.config.get('HIDE_SPARE_PARTS', False):
            filter_context['skip_spare_parts'] = True

        # Field mapping for sorting
        field_mapping = {
            'name': '"rebrickable_parts"."name"',
            'color': '"rebrickable_parts"."color_name"',
            'quantity': '"total_quantity"',
            'missing': '"total_missing"',
            'damaged': '"total_damaged"',
            'sets': '"total_sets"',
            'minifigures': '"total_minifigures"'
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

    # Base part list
    def list(
        self,
        /,
        *,
        override_query: str | None = None,
        order: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        **context: Any,
    ) -> None:
        if order is None:
            order = self.order

        if hasattr(self, 'brickset'):
            brickset = self.brickset
        else:
            brickset = None

        if hasattr(self, 'minifigure'):
            minifigure = self.minifigure
        else:
            minifigure = None

        if hasattr(self, 'individual_minifigure'):
            individual_minifigure = self.individual_minifigure
        else:
            individual_minifigure = None

        # Prepare template context for filtering
        context_vars = {}
        if hasattr(self.fields, 'owner_id') and self.fields.owner_id is not None:
            context_vars['owner_id'] = self.fields.owner_id
        if hasattr(self.fields, 'color_id') and self.fields.color_id is not None:
            context_vars['color_id'] = self.fields.color_id
        if hasattr(self.fields, 'search_query') and self.fields.search_query:
            context_vars['search_query'] = self.fields.search_query

        # Merge with any additional context passed in
        context_vars.update(context)

        # Load the sets from the database
        for record in super().select(
            override_query=override_query,
            order=order,
            limit=limit,
            offset=offset,
            **context_vars
        ):
            part = BrickPart(
                brickset=brickset,
                minifigure=minifigure,
                individual_minifigure=individual_minifigure,
                record=record,
            )

            self.records.append(part)

    # List specific parts from a brickset or minifigure
    def list_specific(
        self,
        brickset: 'BrickSet',
        /,
        *,
        minifigure: 'BrickMinifigure | None' = None,
    ) -> Self:
        # Save the brickset and minifigure
        self.brickset = brickset
        self.minifigure = minifigure

        # Prepare context for hiding spare parts if configured
        context = {}
        if current_app.config.get('HIDE_SPARE_PARTS', False):
            context['skip_spare_parts'] = True

        # Load the parts from the database
        self.list(**context)

        return self

    # Load generic parts from a minifigure
    def from_minifigure(
        self,
        minifigure: 'BrickMinifigure',
        /,
    ) -> Self:
        # Save the  minifigure
        self.minifigure = minifigure

        # Prepare context for hiding spare parts if configured
        context = {}
        if current_app.config.get('HIDE_SPARE_PARTS', False):
            context['skip_spare_parts'] = True

        # Load the parts from the database
        self.list(override_query=self.minifigure_query, **context)

        return self

    # Load parts from an individual minifigure instance
    def from_individual_minifigure(
        self,
        individual_minifigure: 'IndividualMinifigure',
        /,
    ) -> Self:
        from .individual_minifigure import IndividualMinifigure

        # Save the individual minifigure reference
        self.individual_minifigure = individual_minifigure

        # Load the parts for this individual minifigure instance
        self.list(
            override_query='individual_minifigure/part/list/from_instance'
        )

        return self

    # Load generic parts from a print
    def from_print(
        self,
        brickpart: BrickPart,
        /,
    ) -> Self:
        # Save the part and print
        if brickpart.fields.print is not None:
            self.fields.print = brickpart.fields.print
        else:
            self.fields.print = brickpart.fields.part

        self.fields.part = brickpart.fields.part
        self.fields.color = brickpart.fields.color

        # Load the parts from the database
        self.list(override_query=self.print_query)

        return self

    # Last added parts
    def last(self, /, *, limit: int = 6) -> Self:
        if current_app.config['RANDOM']:
            order = 'RANDOM()'
        else:
            # Since bricktracker_parts has a composite primary key, it doesn't have a rowid
            # Order by id DESC (which are UUIDs with timestamps) to get recent parts
            order = '"combined"."id" DESC, "combined"."part" ASC'

        context = {}
        if current_app.config.get('HIDE_SPARE_PARTS', False):
            context['skip_spare_parts'] = True

        self.list(override_query=self.last_query, order=order, limit=limit, **context)

        return self

    # Load problematic parts
    def problem(self, /) -> Self:
        self.list(override_query=self.problem_query)

        return self

    def problem_filtered(self, owner_id: str | None = None, color_id: str | None = None, theme_id: str | None = None, year: str | None = None, storage_id: str | None = None, tag_id: str | None = None, /) -> Self:
        # Save the filter parameters for client-side filtering
        if owner_id is not None:
            self.fields.owner_id = owner_id
        if color_id is not None:
            self.fields.color_id = color_id

        # Prepare context for query
        context = {}
        if owner_id and owner_id != 'all':
            context['owner_id'] = owner_id
        if color_id and color_id != 'all':
            context['color_id'] = color_id
        if theme_id and theme_id != 'all':
            context['theme_id'] = theme_id
        if year and year != 'all':
            context['year'] = year
        if storage_id and storage_id != 'all':
            context['storage_id'] = storage_id
        if tag_id and tag_id != 'all':
            context['tag_id'] = tag_id
        # Hide spare parts from display if configured
        if current_app.config.get('HIDE_SPARE_PARTS', False):
            context['skip_spare_parts'] = True

        # Load the problematic parts from the database
        self.list(override_query=self.problem_query, **context)

        return self

    def problem_paginated(
        self,
        owner_id: str | None = None,
        color_id: str | None = None,
        theme_id: str | None = None,
        year: str | None = None,
        storage_id: str | None = None,
        tag_id: str | None = None,
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
        if color_id and color_id != 'all':
            filter_context['color_id'] = color_id
        if theme_id and theme_id != 'all':
            filter_context['theme_id'] = theme_id
        if year and year != 'all':
            filter_context['year'] = year
        if storage_id and storage_id != 'all':
            filter_context['storage_id'] = storage_id
        if tag_id and tag_id != 'all':
            filter_context['tag_id'] = tag_id
        if search_query:
            filter_context['search_query'] = search_query
        # Hide spare parts from display if configured
        if current_app.config.get('HIDE_SPARE_PARTS', False):
            filter_context['skip_spare_parts'] = True

        # Field mapping for sorting
        field_mapping = {
            'name': '"rebrickable_parts"."name"',
            'color': '"rebrickable_parts"."color_name"',
            'quantity': '"total_quantity"',
            'missing': '"total_missing"',
            'damaged': '"total_damaged"',
            'sets': '"total_sets"',
            'minifigures': '"total_minifigures"'
        }

        # Use the base pagination method with problem query
        return self.paginate(
            page=page,
            per_page=per_page,
            sort_field=sort_field,
            sort_order=sort_order,
            list_query=self.problem_query,
            field_mapping=field_mapping,
            **filter_context
        )

    # Return a dict with common SQL parameters for a parts list
    def sql_parameters(self, /) -> dict[str, Any]:
        parameters: dict[str, Any] = super().sql_parameters()

        # Set id
        if self.brickset is not None:
            parameters['id'] = self.brickset.fields.id

        # Use the individual minifigure ID if present
        if hasattr(self, 'individual_minifigure') and self.individual_minifigure is not None:
            parameters['id'] = self.individual_minifigure.fields.id

        # Use the minifigure number if present,
        if self.minifigure is not None:
            parameters['figure'] = self.minifigure.fields.figure
        else:
            parameters['figure'] = None

        return parameters

    # Load generic parts with same base but different color
    def with_different_color(
        self,
        brickpart: BrickPart,
        /,
    ) -> Self:
        # Save the part
        self.fields.part = brickpart.fields.part
        self.fields.color = brickpart.fields.color

        # Load the parts from the database
        self.list(override_query=self.different_color_query)

        return self

    # Import the parts from Rebrickable
    @staticmethod
    def download(
        socket: 'BrickSocket',
        brickset: 'BrickSet',
        /,
        *,
        minifigure: 'BrickMinifigure | None' = None,
        refresh: bool = False
    ) -> bool:
        if minifigure is not None:
            identifier = minifigure.fields.figure
            kind = 'Minifigure'
            method = 'get_minifig_elements'
        else:
            identifier = brickset.fields.set
            kind = 'Set'
            method = 'get_set_elements'

        try:
            socket.auto_progress(
                message='{kind} {identifier}: loading parts inventory from the BrickLink catalog'.format(  # noqa: E501
                    kind=kind,
                    identifier=identifier,
                ),
                increment_total=True,
            )

            logger.debug('BrickLink catalog {method}("{identifier}")'.format(  # noqa: E501
                method=method,
                identifier=identifier,
            ))

            inventory = BrickLink[BrickPart](
                method,
                identifier,
                BrickPart,
                socket=socket,
                brickset=brickset,
                minifigure=minifigure,
            ).list()

            # Process each part
            number_of_parts: int = 0
            skip_spares = current_app.config.get('SKIP_SPARE_PARTS', False)

            for part in inventory:
                # Skip spare parts if configured
                if skip_spares and part.fields.spare:
                    continue

                # Count the number of parts for minifigures
                if minifigure is not None:
                    number_of_parts += part.fields.quantity

                if not part.download(socket, refresh=refresh):
                    return False

            if minifigure is not None:
                minifigure.fields.number_of_parts = number_of_parts

        except Exception as e:
            socket.fail(
                message='Error while importing {kind} {identifier} parts list: {error}'.format(  # noqa: E501
                    kind=kind,
                    identifier=identifier,
                    error=e,
                )
            )

            logger.debug(traceback.format_exc())

            return False

        return True
