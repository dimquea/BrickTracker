from typing import Any, Final

# Configuration map:
# - n: internal name (str)
# - e: extra environment name (str, optional=None)
# - d: default value (Any, optional=None)
# - c: cast to type (Type, optional=None)
# - s: interpret as a path within static (bool, optional=False)
# Easy to change an environment variable name without changing all the code
CONFIG: Final[list[dict[str, Any]]] = [
    {'n': 'AUTHENTICATION_PASSWORD', 'd': ''},
    {'n': 'AUTHENTICATION_KEY', 'd': ''},
    {'n': 'BRICKLINK_LINK_PART_PATTERN', 'd': 'https://www.bricklink.com/v2/catalog/catalogitem.page?P={part}&C={color}'},  # noqa: E501
    {'n': 'BRICKLINK_LINK_SET_PATTERN', 'd': 'https://www.bricklink.com/v2/catalog/catalogitem.page?S={set_num}'},  # noqa: E501
    {'n': 'BRICKLINK_LINKS', 'c': bool},
    {'n': 'DATABASE_PATH', 'd': './app.db'},
    {'n': 'DATABASE_TIMESTAMP_FORMAT', 'd': '%Y-%m-%d-%H-%M-%S'},
    {'n': 'DEBUG', 'c': bool},
    {'n': 'DEFAULT_TABLE_PER_PAGE', 'd': 25, 'c': int},
    {'n': 'DESCRIPTION_BADGE_MAX_LENGTH', 'd': 15, 'c': int},
    {'n': 'DISABLE_INDIVIDUAL_MINIFIGURES', 'c': bool},
    {'n': 'DOMAIN_NAME', 'e': 'DOMAIN_NAME', 'd': ''},
    {'n': 'FILE_DATETIME_FORMAT', 'd': '%d/%m/%Y, %H:%M:%S'},
    {'n': 'HOST', 'd': '0.0.0.0'},
    {'n': 'INDEPENDENT_ACCORDIONS', 'c': bool},
    {'n': 'INSTRUCTIONS_ALLOWED_EXTENSIONS', 'd': ['.pdf'], 'c': list},  # noqa: E501
    {'n': 'INSTRUCTIONS_FOLDER', 'd': 'instructions', 's': True},
    {'n': 'HIDE_ADD_SET', 'c': bool},
    {'n': 'HIDE_ADD_BULK_SET', 'c': bool},
    {'n': 'HIDE_ADMIN', 'c': bool},
    {'n': 'ADMIN_DEFAULT_EXPANDED_SECTIONS', 'd': ['database'], 'c': list},
    {'n': 'HIDE_ALL_INSTRUCTIONS', 'c': bool},
    {'n': 'HIDE_ALL_MINIFIGURES', 'c': bool},
    {'n': 'HIDE_ALL_PARTS', 'c': bool},
    {'n': 'HIDE_ALL_PROBLEMS_PARTS', 'e': 'BK_HIDE_MISSING_PARTS', 'c': bool},
    {'n': 'HIDE_ALL_SETS', 'c': bool},
    {'n': 'HIDE_ALL_STORAGES', 'c': bool},
    {'n': 'HIDE_STATISTICS', 'c': bool},
    {'n': 'HIDE_SET_INSTRUCTIONS', 'c': bool},
    {'n': 'HIDE_TABLE_DAMAGED_PARTS', 'c': bool},
    {'n': 'HIDE_TABLE_MISSING_PARTS', 'c': bool},
    {'n': 'HIDE_TABLE_CHECKED_PARTS', 'c': bool},
    {'n': 'HIDE_WISHES', 'c': bool},
    {'n': 'MINIFIGURES_DEFAULT_ORDER', 'd': '"combined"."name" ASC'},  # noqa: E501
    {'n': 'MINIFIGURES_FOLDER', 'd': 'minifigures', 's': True},
    {'n': 'MINIFIGURES_PAGINATION_SIZE_DESKTOP', 'd': 10, 'c': int},
    {'n': 'MINIFIGURES_PAGINATION_SIZE_MOBILE', 'd': 5, 'c': int},
    {'n': 'MINIFIGURES_SERVER_SIDE_PAGINATION', 'c': bool},
    {'n': 'NO_THREADED_SOCKET', 'c': bool},
    {'n': 'PARTS_SERVER_SIDE_PAGINATION', 'c': bool},
    {'n': 'SETS_SERVER_SIDE_PAGINATION', 'c': bool},
    {'n': 'PARTS_DEFAULT_ORDER', 'd': '"rebrickable_parts"."name" ASC, "rebrickable_parts"."color_name" ASC, "combined"."spare" ASC'},  # noqa: E501
    {'n': 'PARTS_FOLDER', 'd': 'parts', 's': True},
    {'n': 'PARTS_PAGINATION_SIZE_DESKTOP', 'd': 10, 'c': int},
    {'n': 'PARTS_PAGINATION_SIZE_MOBILE', 'd': 5, 'c': int},
    {'n': 'PROBLEMS_PAGINATION_SIZE_DESKTOP', 'd': 10, 'c': int},
    {'n': 'PROBLEMS_PAGINATION_SIZE_MOBILE', 'd': 10, 'c': int},
    {'n': 'PROBLEMS_SERVER_SIDE_PAGINATION', 'c': bool},
    {'n': 'SETS_PAGINATION_SIZE_DESKTOP', 'd': 12, 'c': int},
    {'n': 'SETS_PAGINATION_SIZE_MOBILE', 'd': 4, 'c': int},
    {'n': 'PORT', 'd': 3333, 'c': int},
    {'n': 'PURCHASE_DATE_FORMAT', 'd': '%d/%m/%Y'},
    {'n': 'PURCHASE_CURRENCY', 'd': '€'},
    {'n': 'PURCHASE_LOCATION_DEFAULT_ORDER', 'd': '"bricktracker_metadata_purchase_locations"."name" ASC'},  # noqa: E501
    {'n': 'RANDOM', 'e': 'RANDOM', 'c': bool},
    {'n': 'REBRICKABLE_API_KEY', 'e': 'REBRICKABLE_API_KEY', 'd': ''},
    {'n': 'REBRICKABLE_IMAGE_NIL', 'd': 'https://rebrickable.com/static/img/nil.png'},  # noqa: E501
    {'n': 'REBRICKABLE_IMAGE_NIL_MINIFIGURE', 'd': 'https://rebrickable.com/static/img/nil_mf.jpg'},  # noqa: E501
    {'n': 'REBRICKABLE_LINK_MINIFIGURE_PATTERN', 'd': 'https://rebrickable.com/minifigs/{figure}'},  # noqa: E501
    {'n': 'REBRICKABLE_LINK_PART_PATTERN', 'd': 'https://rebrickable.com/parts/{part}/_/{color}'},  # noqa: E501
    {'n': 'REBRICKABLE_LINK_INSTRUCTIONS_PATTERN', 'd': 'https://rebrickable.com/instructions/{path}'},  # noqa: E501
    {'n': 'REBRICKABLE_USER_AGENT', 'd': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'},  # noqa: E501
    {'n': 'USER_AGENT', 'd': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'},  # noqa: E501
    {'n': 'PEERON_DOWNLOAD_DELAY', 'd': 1000, 'c': int},
    {'n': 'PEERON_INSTRUCTION_PATTERN', 'd': 'http://peeron.com/scans/{set_number}-{version_number}'},
    {'n': 'PEERON_MIN_IMAGE_SIZE', 'd': 100, 'c': int},
    {'n': 'PEERON_SCAN_PATTERN', 'd': 'http://belay.peeron.com/scans/{set_number}-{version_number}/'},
    {'n': 'PEERON_THUMBNAIL_PATTERN', 'd': 'http://belay.peeron.com/thumbs/{set_number}-{version_number}/'},
    {'n': 'REBRICKABLE_LINKS', 'e': 'LINKS', 'c': bool},
    {'n': 'REBRICKABLE_PAGE_SIZE', 'd': 100, 'c': int},
    {'n': 'RETIRED_SETS_FILE_URL', 'd': 'https://docs.google.com/spreadsheets/d/1rlYfEXtNKxUOZt2Mfv0H17DvK7bj6Pe0CuYwq6ay8WA/gviz/tq?tqx=out:csv&sheet=Sorted%20by%20Retirement%20Date'},  # noqa: E501
    {'n': 'RETIRED_SETS_PATH', 'd': './retired_sets.csv'},
    {'n': 'SETS_DEFAULT_ORDER', 'd': '"rebrickable_sets"."number" DESC, "rebrickable_sets"."version" ASC'},  # noqa: E501
    {'n': 'SETS_FOLDER', 'd': 'sets', 's': True},
    {'n': 'SETS_CONSOLIDATION', 'd': False, 'c': bool},
    {'n': 'SHOW_GRID_FILTERS', 'c': bool},
    {'n': 'SHOW_GRID_SORT', 'c': bool},
    {'n': 'SHOW_SETS_DUPLICATE_FILTER', 'd': True, 'c': bool},
    {'n': 'SKIP_SPARE_PARTS', 'c': bool},
    {'n': 'SOCKET_NAMESPACE', 'd': 'bricksocket'},
    {'n': 'SOCKET_PATH', 'd': '/bricksocket/'},
    {'n': 'STORAGE_DEFAULT_ORDER', 'd': '"bricktracker_metadata_storages"."name" ASC'},  # noqa: E501
    {'n': 'THEMES_FILE_URL', 'd': 'https://cdn.rebrickable.com/media/downloads/themes.csv.gz'},  # noqa: E501
    {'n': 'THEMES_PATH', 'd': './themes.csv'},
    {'n': 'TIMEZONE', 'd': 'Etc/UTC'},
    {'n': 'USE_REMOTE_IMAGES', 'c': bool},
    {'n': 'WISHES_DEFAULT_ORDER', 'd': '"bricktracker_wishes"."rowid" DESC'},
    {'n': 'STATISTICS_SHOW_CHARTS', 'd': True, 'c': bool},
    {'n': 'STATISTICS_DEFAULT_EXPANDED', 'd': True, 'c': bool},
]
