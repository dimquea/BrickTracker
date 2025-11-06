import logging
import sys
import time
from zoneinfo import ZoneInfo

from flask import current_app, Flask, g
from werkzeug.middleware.proxy_fix import ProxyFix

from bricktracker.configuration_list import BrickConfigurationList
from bricktracker.login import LoginManager
from bricktracker.navbar import Navbar
from bricktracker.sql import close
from bricktracker.template_filters import replace_query_filter
from bricktracker.version import __version__
from bricktracker.views.add import add_page
from bricktracker.views.admin.admin import admin_page
from bricktracker.views.admin.database import admin_database_page
from bricktracker.views.admin.image import admin_image_page
from bricktracker.views.admin.instructions import admin_instructions_page
from bricktracker.views.admin.owner import admin_owner_page
from bricktracker.views.admin.purchase_location import admin_purchase_location_page  # noqa: E501
from bricktracker.views.admin.retired import admin_retired_page
from bricktracker.views.admin.set import admin_set_page
from bricktracker.views.admin.status import admin_status_page
from bricktracker.views.admin.storage import admin_storage_page
from bricktracker.views.admin.tag import admin_tag_page
from bricktracker.views.admin.theme import admin_theme_page
from bricktracker.views.error import error_404
from bricktracker.views.index import index_page
from bricktracker.views.instructions import instructions_page
from bricktracker.views.login import login_page
from bricktracker.views.individual_minifigure import individual_minifigure_page
from bricktracker.views.individual_part import individual_part_page
from bricktracker.views.minifigure import minifigure_page
from bricktracker.views.part import part_page
from bricktracker.views.set import set_page
from bricktracker.views.statistics import statistics_page
from bricktracker.views.storage import storage_page
from bricktracker.views.wish import wish_page

logger = logging.getLogger(__name__)


def _validate_config(app: Flask) -> None:
    """
    Validate application configuration and log warnings for potential issues.
    """
    # Check if both individual features are disabled
    if app.config.get('DISABLE_INDIVIDUAL_PARTS') and app.config.get('DISABLE_INDIVIDUAL_MINIFIGURES'):
        logger.warning(
            'Both DISABLE_INDIVIDUAL_PARTS and DISABLE_INDIVIDUAL_MINIFIGURES are enabled. '
            'Users will not be able to track standalone parts or minifigures.'
        )

    # Check if Rebrickable API key is missing
    if not app.config.get('REBRICKABLE_API_KEY'):
        logger.warning(
            'REBRICKABLE_API_KEY is not set. You will not be able to fetch data from Rebrickable API. '
            'Please set this in your .env file or environment variables.'
        )

    # Check authentication configuration
    if not app.config.get('AUTHENTICATION_PASSWORD') and not app.config.get('AUTHENTICATION_KEY'):
        logger.info(
            'No authentication configured (AUTHENTICATION_PASSWORD or AUTHENTICATION_KEY). '
            'Admin features will be accessible without login.'
        )


def setup_app(app: Flask) -> None:
    # Load the configuration
    BrickConfigurationList(app)

    # Validate configuration
    _validate_config(app)

    # Set the logging level
    if app.config['DEBUG']:
        logging.basicConfig(
            stream=sys.stdout,
            level=logging.DEBUG,
            format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',  # noqa: E501
        )
    else:
        logging.basicConfig(
            stream=sys.stdout,
            level=logging.INFO,
            format='[%(asctime)s] %(levelname)s - %(message)s',
        )

    # Load the navbar
    Navbar(app)

    # Setup the login manager
    LoginManager(app)

    # Configure proxy header handling for reverse proxy deployments (nginx, Apache, etc.)
    # This ensures proper client IP detection and HTTPS scheme recognition
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,
        x_proto=1,
        x_host=1,
        x_port=1,
        x_prefix=1,
    )

    # Register errors
    app.register_error_handler(404, error_404)

    # Register app routes
    app.register_blueprint(add_page)
    app.register_blueprint(index_page)
    app.register_blueprint(instructions_page)
    app.register_blueprint(login_page)
    app.register_blueprint(individual_minifigure_page)
    app.register_blueprint(individual_part_page)
    app.register_blueprint(minifigure_page)
    app.register_blueprint(part_page)
    app.register_blueprint(set_page)
    app.register_blueprint(statistics_page)
    app.register_blueprint(storage_page)
    app.register_blueprint(wish_page)

    # Register admin routes
    app.register_blueprint(admin_page)
    app.register_blueprint(admin_database_page)
    app.register_blueprint(admin_image_page)
    app.register_blueprint(admin_instructions_page)
    app.register_blueprint(admin_retired_page)
    app.register_blueprint(admin_owner_page)
    app.register_blueprint(admin_purchase_location_page)
    app.register_blueprint(admin_set_page)
    app.register_blueprint(admin_status_page)
    app.register_blueprint(admin_storage_page)
    app.register_blueprint(admin_tag_page)
    app.register_blueprint(admin_theme_page)

    # An helper to make global variables available to the
    # request
    @app.before_request
    def before_request() -> None:
        def request_time() -> str:
            elapsed = time.time() - g.request_start_time
            if elapsed < 1:
                return '{elapsed:.0f}ms'.format(elapsed=elapsed*1000)
            else:
                return '{elapsed:.2f}s'.format(elapsed=elapsed)

        # Login manager
        g.login = LoginManager

        # Execution time
        g.request_start_time = time.time()
        g.request_time = request_time

        # Register the timezone
        g.timezone = ZoneInfo(current_app.config['TIMEZONE'])

        # Version
        g.version = __version__

    # Register custom Jinja2 filters
    app.jinja_env.filters['replace_query'] = replace_query_filter

    # Make sure all connections are closed at the end
    @app.teardown_request
    def teardown_request(_: BaseException | None) -> None:
        close()
