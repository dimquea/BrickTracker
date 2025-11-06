from flask import Blueprint, render_template, request, current_app

from .exceptions import exception_handler
from ..individual_part_list import IndividualPartList
from ..minifigure_list import BrickMinifigureList
from ..pagination_helper import get_pagination_config, build_pagination_context, get_request_params
from ..part import BrickPart
from ..part_list import BrickPartList
from ..set_list import BrickSetList, set_metadata_lists
from ..set_owner_list import BrickSetOwnerList
from ..sql import BrickSQL

part_page = Blueprint('part', __name__, url_prefix='/parts')


# Index
@part_page.route('/', methods=['GET'])
@exception_handler(__file__)
def list() -> str:
    # Get filter parameters from request
    owner_id = request.args.get('owner', 'all')
    color_id = request.args.get('color', 'all')
    search_query, sort_field, sort_order, page = get_request_params()

    # Get pagination configuration
    per_page, is_mobile = get_pagination_config('parts')
    use_pagination = per_page > 0

    if use_pagination:
        # PAGINATION MODE - Server-side pagination with search
        parts, total_count = BrickPartList().all_filtered_paginated(
            owner_id=owner_id,
            color_id=color_id,
            search_query=search_query,
            page=page,
            per_page=per_page,
            sort_field=sort_field,
            sort_order=sort_order
        )

        pagination_context = build_pagination_context(page, per_page, total_count, is_mobile)
    else:
        # ORIGINAL MODE - Single page with all data for client-side search
        parts = BrickPartList().all_filtered(owner_id, color_id)
        pagination_context = None

    # Get list of owners for filter dropdown
    owners = BrickSetOwnerList.list()

    # Get list of colors for filter dropdown
    # Prepare context for color query (filter by owner if selected)
    color_context = {}
    if owner_id != 'all' and owner_id:
        color_context['owner_id'] = owner_id

    colors = BrickSQL().fetchall('part/colors/list', **color_context)

    template_context = {
        'table_collection': parts,
        'owners': owners,
        'selected_owner': owner_id,
        'colors': colors,
        'selected_color': color_id,
        'search_query': search_query,
        'use_pagination': use_pagination,
        'current_sort': sort_field,
        'current_order': sort_order
    }

    if pagination_context:
        template_context['pagination'] = pagination_context

    return render_template('parts.html', **template_context)



# Problem
@part_page.route('/problem', methods=['GET'])
@exception_handler(__file__)
def problem() -> str:
    # Get filter parameters from request
    owner_id = request.args.get('owner', 'all')
    color_id = request.args.get('color', 'all')
    search_query, sort_field, sort_order, page = get_request_params()

    # Get pagination configuration
    per_page, is_mobile = get_pagination_config('problems')
    use_pagination = per_page > 0

    if use_pagination:
        # PAGINATION MODE - Server-side pagination with search and filters
        parts, total_count = BrickPartList().problem_paginated(
            owner_id=owner_id,
            color_id=color_id,
            search_query=search_query,
            page=page,
            per_page=per_page,
            sort_field=sort_field,
            sort_order=sort_order
        )

        pagination_context = build_pagination_context(page, per_page, total_count, is_mobile)
    else:
        # ORIGINAL MODE - Single page with all data for client-side search
        parts = BrickPartList().problem_filtered(owner_id, color_id)
        pagination_context = None

    # Get list of owners for filter dropdown
    owners = BrickSetOwnerList.list()

    # Get list of colors for filter dropdown
    # Prepare context for color query (filter by owner if selected)
    color_context = {}
    if owner_id != 'all':
        color_context['owner_id'] = owner_id

    # Get colors from problem parts (following same pattern as parts page)
    colors = BrickSQL().fetchall('part/colors/list_problem', **color_context)

    return render_template(
        'problem.html',
        table_collection=parts,
        pagination=pagination_context,
        search_query=search_query,
        sort_field=sort_field,
        sort_order=sort_order,
        use_pagination=use_pagination,
        owners=owners,
        colors=colors,
        selected_owner=owner_id,
        selected_color=color_id
    )


# Part details
@part_page.route('/<part>/<int:color>/details', methods=['GET'])  # noqa: E501
@exception_handler(__file__)
def details(*, part: str, color: int) -> str:
    brickpart = BrickPart().select_generic(part, color)

    # Get individual parts if not disabled
    individual_parts = None
    if not current_app.config.get('DISABLE_INDIVIDUAL_PARTS', False):
        individual_parts = IndividualPartList().by_part_and_color(part, color)

    return render_template(
        'part.html',
        item=brickpart,
        sets_using=BrickSetList().using_part(
            part,
            color
        ),
        sets_missing=BrickSetList().missing_part(
            part,
            color
        ),
        sets_damaged=BrickSetList().damaged_part(
            part,
            color
        ),
        minifigures_using=BrickMinifigureList().using_part(
            part,
            color
        ),
        minifigures_missing=BrickMinifigureList().missing_part(
            part,
            color
        ),
        minifigures_damaged=BrickMinifigureList().damaged_part(
            part,
            color
        ),
        different_color=BrickPartList().with_different_color(brickpart),
        similar_prints=BrickPartList().from_print(brickpart),
        individual_parts=individual_parts,
        **set_metadata_lists(as_class=True)
    )
