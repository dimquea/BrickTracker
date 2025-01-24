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
    {'n': 'BRICKLINK_LINK_PART_PATTERN', 'd': 'https://www.bricklink.com/v2/catalog/catalogitem.page?P={number}'},  # noqa: E501
    {'n': 'BRICKLINK_LINKS', 'c': bool},
    {'n': 'DATABASE_PATH', 'd': './app.db'},
    {'n': 'DATABASE_TIMESTAMP_FORMAT', 'd': '%Y-%m-%d-%H-%M-%S'},
    {'n': 'DEBUG', 'c': bool},
    {'n': 'DEFAULT_TABLE_PER_PAGE', 'd': 25, 'c': int},
    {'n': 'DOMAIN_NAME', 'e': 'DOMAIN_NAME', 'd': ''},
    {'n': 'FILE_DATETIME_FORMAT', 'd': '%d/%m/%Y, %H:%M:%S'},
    {'n': 'HOST', 'd': '0.0.0.0'},
    {'n': 'INDEPENDENT_ACCORDIONS', 'c': bool},
    {'n': 'INSTRUCTIONS_ALLOWED_EXTENSIONS', 'd': ['.pdf'], 'c': list},  # noqa: E501
    {'n': 'INSTRUCTIONS_FOLDER', 'd': 'instructions', 's': True},
    {'n': 'HIDE_ADD_SET', 'c': bool},
    {'n': 'HIDE_ADD_BULK_SET', 'c': bool},
    {'n': 'HIDE_ADMIN', 'c': bool},
    {'n': 'HIDE_ALL_INSTRUCTIONS', 'c': bool},
    {'n': 'HIDE_ALL_MINIFIGURES', 'c': bool},
    {'n': 'HIDE_ALL_PARTS', 'c': bool},
    {'n': 'HIDE_ALL_SETS', 'c': bool},
    {'n': 'HIDE_MISSING_PARTS', 'c': bool},
    {'n': 'HIDE_WISHES', 'c': bool},
    {'n': 'MINIFIGURES_DEFAULT_ORDER', 'd': '"minifigures"."name" ASC'},
    {'n': 'MINIFIGURES_FOLDER', 'd': 'minifigs', 's': True},
    {'n': 'NO_THREADED_SOCKET', 'c': bool},
    {'n': 'PARTS_DEFAULT_ORDER', 'd': '"inventory"."name" ASC, "inventory"."color_name" ASC, "inventory"."is_spare" ASC'},  # noqa: E501
    {'n': 'PARTS_FOLDER', 'd': 'parts', 's': True},
    {'n': 'PORT', 'd': 3333, 'c': int},
    {'n': 'RANDOM', 'e': 'RANDOM', 'c': bool},
    {'n': 'REBRICKABLE_API_KEY', 'e': 'REBRICKABLE_API_KEY', 'd': ''},
    {'n': 'REBRICKABLE_IMAGE_NIL', 'd': 'https://rebrickable.com/static/img/nil.png'},  # noqa: E501
    {'n': 'REBRICKABLE_IMAGE_NIL_MINIFIGURE', 'd': 'https://rebrickable.com/static/img/nil_mf.jpg'},  # noqa: E501
    {'n': 'REBRICKABLE_LINK_MINIFIGURE_PATTERN', 'd': 'https://rebrickable.com/minifigs/{number}'},  # noqa: E501
    {'n': 'REBRICKABLE_LINK_PART_PATTERN', 'd': 'https://rebrickable.com/parts/{number}/_/{color}'},  # noqa: E501
    {'n': 'REBRICKABLE_LINK_INSTRUCTIONS_PATTERN', 'd': 'https://rebrickable.com/instructions/{number}'},  # noqa: E501
    {'n': 'REBRICKABLE_USER_AGENT', 'd': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'},
    {'n': 'REBRICKABLE_LINKS', 'e': 'LINKS', 'c': bool},
    {'n': 'REBRICKABLE_PAGE_SIZE', 'd': 100, 'c': int},
    {'n': 'RETIRED_SETS_FILE_URL', 'd': 'https://docs.google.com/spreadsheets/d/1rlYfEXtNKxUOZt2Mfv0H17DvK7bj6Pe0CuYwq6ay8WA/gviz/tq?tqx=out:csv&sheet=Sorted%20by%20Retirement%20Date'},  # noqa: E501
    {'n': 'RETIRED_SETS_PATH', 'd': './retired_sets.csv'},
    {'n': 'SETS_DEFAULT_ORDER', 'd': '"rebrickable_sets"."number" DESC, "rebrickable_sets"."version" ASC'},  # noqa: E501
    {'n': 'SETS_FOLDER', 'd': 'sets', 's': True},
    {'n': 'SKIP_SPARE_PARTS', 'c': bool},
    {'n': 'SOCKET_NAMESPACE', 'd': 'bricksocket'},
    {'n': 'SOCKET_PATH', 'd': '/bricksocket/'},
    {'n': 'THEMES_FILE_URL', 'd': 'https://cdn.rebrickable.com/media/downloads/themes.csv.gz'},  # noqa: E501
    {'n': 'THEMES_PATH', 'd': './themes.csv'},
    {'n': 'TIMEZONE', 'd': 'Etc/UTC'},
    {'n': 'USE_REMOTE_IMAGES', 'c': bool},
    {'n': 'WISHES_DEFAULT_ORDER', 'd': '"bricktracker_wishes"."rowid" DESC'},
]
