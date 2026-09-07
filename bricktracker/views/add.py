from flask import Blueprint, current_app, render_template, abort
from flask_login import login_required

from ..bricklink_catalog import error_unless_catalog
from .exceptions import exception_handler
from ..set_list import set_metadata_lists
from ..set_status_list import BrickSetStatusList
from ..socket import MESSAGES

add_page = Blueprint('add', __name__, url_prefix='/add')


# Add a set
@add_page.route('/', methods=['GET'])
@login_required
@exception_handler(__file__)
def add() -> str:
    error_unless_catalog()

    return render_template(
        'add.html',
        path=current_app.config['SOCKET_PATH'],
        namespace=current_app.config['SOCKET_NAMESPACE'],
        messages=MESSAGES,
        brickset_statuses=BrickSetStatusList.list(all=True),
        **set_metadata_lists()
    )


# Bulk add sets
@add_page.route('/bulk', methods=['GET'])
@login_required
@exception_handler(__file__)
def bulk() -> str:
    error_unless_catalog()

    return render_template(
        'add.html',
        path=current_app.config['SOCKET_PATH'],
        namespace=current_app.config['SOCKET_NAMESPACE'],
        messages=MESSAGES,
        bulk=True,
        brickset_statuses=BrickSetStatusList.list(all=True),
        **set_metadata_lists()
    )


# Add individual parts
@add_page.route('/parts', methods=['GET'])
@login_required
@exception_handler(__file__)
def parts() -> str:
    # Block route if individual parts feature is disabled
    if current_app.config.get('DISABLE_INDIVIDUAL_PARTS', False):
        abort(404)

    error_unless_catalog()

    return render_template(
        'add_parts.html',
        path=current_app.config['SOCKET_PATH'],
        namespace=current_app.config['SOCKET_NAMESPACE'],
        messages=MESSAGES,
        **set_metadata_lists()
    )
