from flask import Blueprint, current_app, render_template, request

from .exceptions import exception_handler
from ..minifigure import BrickMinifigure
from ..minifigure_list import BrickMinifigureList
from ..individual_minifigure_list import IndividualMinifigureList
from ..pagination_helper import get_pagination_config, build_pagination_context, get_request_params
from ..set_list import BrickSetList, set_metadata_lists
from ..set_owner_list import BrickSetOwnerList

minifigure_page = Blueprint('minifigure', __name__, url_prefix='/minifigures')


# Index
@minifigure_page.route('/', methods=['GET'])
@exception_handler(__file__)
def list() -> str:
    # Get filter parameters from request
    owner_id = request.args.get('owner', 'all')
    search_query, sort_field, sort_order, page = get_request_params()

    # Get pagination configuration
    per_page, is_mobile = get_pagination_config('minifigures')
    use_pagination = per_page > 0

    if use_pagination:
        # PAGINATION MODE - Server-side pagination with search
        minifigures, total_count = BrickMinifigureList().all_filtered_paginated(
            owner_id=owner_id,
            search_query=search_query,
            page=page,
            per_page=per_page,
            sort_field=sort_field,
            sort_order=sort_order
        )

        pagination_context = build_pagination_context(page, per_page, total_count, is_mobile)
    else:
        # ORIGINAL MODE - Single page with all data for client-side search
        if owner_id == 'all' or owner_id is None or owner_id == '':
            minifigures = BrickMinifigureList().all()
        else:
            minifigures = BrickMinifigureList().all_by_owner(owner_id)

        pagination_context = None

    # Get list of owners for filter dropdown
    owners = BrickSetOwnerList.list()

    template_context = {
        'table_collection': minifigures,
        'owners': owners,
        'selected_owner': owner_id,
        'search_query': search_query,
        'use_pagination': use_pagination,
        'current_sort': sort_field,
        'current_order': sort_order
    }

    if pagination_context:
        template_context['pagination'] = pagination_context

    return render_template('minifigures.html', **template_context)


# Minifigure details
@minifigure_page.route('/<figure>/details')
@exception_handler(__file__)
def details(*, figure: str) -> str:
    return render_template(
        'minifigure.html',
        item=BrickMinifigure().select_generic(figure),
        using=BrickSetList().using_minifigure(figure),
        missing=BrickSetList().missing_minifigure(figure),
        damaged=BrickSetList().damaged_minifigure(figure),
        individual_instances=IndividualMinifigureList().instances_by_figure(figure),
        **set_metadata_lists(as_class=True)
    )
