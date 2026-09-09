from flask import Blueprint, current_app, render_template, request

from .exceptions import exception_handler
from ..individual_minifigure_list import IndividualMinifigureList
from ..individual_part_list import IndividualPartList
from ..individual_part_lot_list import IndividualPartLotList
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
    theme_id = request.args.get('theme', 'all')
    year = request.args.get('year', 'all')
    individuals_filter = request.args.get('individuals', 'all')
    search_query, sort_field, sort_order, page = get_request_params()

    # Get pagination configuration
    per_page, is_mobile = get_pagination_config('parts')
    use_pagination = per_page > 0

    if use_pagination:
        # PAGINATION MODE - Server-side pagination with search
        parts, total_count = BrickPartList().all_filtered_paginated(
            owner_id=owner_id,
            color_id=color_id,
            theme_id=theme_id,
            year=year,
            individuals_filter=individuals_filter,
            search_query=search_query,
            page=page,
            per_page=per_page,
            sort_field=sort_field,
            sort_order=sort_order
        )

        pagination_context = build_pagination_context(page, per_page, total_count, is_mobile)
    else:
        # ORIGINAL MODE - Single page with all data for client-side search
        parts = BrickPartList().all_filtered(owner_id, color_id, theme_id, year, individuals_filter)
        pagination_context = None

    # Get list of owners for filter dropdown
    owners = BrickSetOwnerList.list()

    # Prepare context for dependent filters
    filter_context = {}
    if owner_id != 'all' and owner_id:
        filter_context['owner_id'] = owner_id

    # Get list of colors for filter dropdown
    colors = BrickSQL().fetchall('part/colors/list', **filter_context)

    # Get list of themes for filter dropdown
    from ..theme_list import BrickThemeList
    theme_list = BrickThemeList()
    themes_data = BrickSQL().fetchall('part/themes/list', **filter_context)
    themes = []
    for theme_data in themes_data:
        theme = theme_list.get(theme_data['theme_id'])
        themes.append({
            'theme_id': theme_data['theme_id'],
            'theme_name': theme.name if theme else f"Theme {theme_data['theme_id']}"
        })

    # Get list of years for filter dropdown
    years = BrickSQL().fetchall('part/years/list', **filter_context)

    template_context = {
        'table_collection': parts,
        'owners': owners,
        'selected_owner': owner_id,
        'colors': colors,
        'selected_color': color_id,
        'themes': themes,
        'selected_theme': theme_id,
        'years': years,
        'selected_year': year,
        'selected_individuals': individuals_filter,
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
    theme_id = request.args.get('theme', 'all')
    year = request.args.get('year', 'all')
    storage_id = request.args.get('storage', 'all')
    tag_id = request.args.get('tag', 'all')
    search_query, sort_field, sort_order, page = get_request_params()

    # Get pagination configuration
    per_page, is_mobile = get_pagination_config('problems')
    use_pagination = per_page > 0

    if use_pagination:
        # PAGINATION MODE - Server-side pagination with search and filters
        parts, total_count = BrickPartList().problem_paginated(
            owner_id=owner_id,
            color_id=color_id,
            theme_id=theme_id,
            year=year,
            storage_id=storage_id,
            tag_id=tag_id,
            search_query=search_query,
            page=page,
            per_page=per_page,
            sort_field=sort_field,
            sort_order=sort_order
        )

        pagination_context = build_pagination_context(page, per_page, total_count, is_mobile)
    else:
        # ORIGINAL MODE - Single page with all data for client-side search
        parts = BrickPartList().problem_filtered(owner_id, color_id, theme_id, year, storage_id, tag_id)
        pagination_context = None

    # Get list of owners for filter dropdown
    owners = BrickSetOwnerList.list()

    # Prepare context for dependent filters
    filter_context = {}
    if owner_id != 'all' and owner_id:
        filter_context['owner_id'] = owner_id

    # Get list of colors for filter dropdown (problem parts only)
    colors = BrickSQL().fetchall('part/colors/list_problem', **filter_context)

    # Get list of themes for filter dropdown (problem parts only)
    from ..theme_list import BrickThemeList
    theme_list = BrickThemeList()
    themes_data = BrickSQL().fetchall('part/themes/list_problem', **filter_context)
    themes = []
    for theme_data in themes_data:
        theme = theme_list.get(theme_data['theme_id'])
        themes.append({
            'theme_id': theme_data['theme_id'],
            'theme_name': theme.name if theme else f"Theme {theme_data['theme_id']}"
        })

    # Get list of years for filter dropdown (problem parts only)
    years = BrickSQL().fetchall('part/years/list_problem', **filter_context)

    # Get list of storages for filter dropdown (problem parts only)
    storages = BrickSQL().fetchall('part/storages/list_problem', **filter_context)

    # Get list of tags for filter dropdown (problem parts only)
    tags = BrickSQL().fetchall('part/tags/list_problem', **filter_context)

    # Фигурки с отметками идут отдельной секцией: у фигурки нет цвета, а
    # именно цвет держит сортировку и фильтры таблицы деталей, да и
    # считается фигурка не как деталь
    problem_minifigures = BrickMinifigureList().problem()

    return render_template(
        'problem.html',
        table_collection=parts,
        problem_minifigures=problem_minifigures.records,
        pagination=pagination_context,
        search_query=search_query,
        sort_field=sort_field,
        sort_order=sort_order,
        use_pagination=use_pagination,
        owners=owners,
        colors=colors,
        selected_owner=owner_id,
        selected_color=color_id,
        themes=themes,
        selected_theme=theme_id,
        years=years,
        selected_year=year,
        storages=storages,
        selected_storage=storage_id,
        tags=tags,
        selected_tag=tag_id
    )


# Part details
@part_page.route('/<part>/<int:color>/details', methods=['GET'])  # noqa: E501
@exception_handler(__file__)
def details(*, part: str, color: int) -> str:
    brickpart = BrickPart().select_generic(part, color)

    writes_disabled = current_app.config.get('DISABLE_INDIVIDUAL_PARTS', False)

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
        individual_minifigures_using=IndividualMinifigureList().using_part(
            part,
            color
        ),
        individual_minifigures_missing=IndividualMinifigureList().missing_part(
            part,
            color
        ),
        individual_minifigures_damaged=IndividualMinifigureList().damaged_part(
            part,
            color
        ),
        individual_parts=IndividualPartList().by_part_and_color(part, color),
        individual_lots=IndividualPartLotList().by_part_and_color(part, color),
        writes_disabled=writes_disabled,
        **set_metadata_lists(as_class=True)
    )
