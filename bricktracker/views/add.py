from flask import Blueprint, current_app, render_template
from flask_login import login_required

from ..configuration_list import BrickConfigurationList
from .exceptions import exception_handler
from ..set_list import set_metadata_lists
from ..socket import MESSAGES

add_page = Blueprint('add', __name__, url_prefix='/add')


# Add a set
@add_page.route('/', methods=['GET'])
@login_required
@exception_handler(__file__)
def add() -> str:
    BrickConfigurationList.error_unless_is_set('REBRICKABLE_API_KEY')

    return render_template(
        'add.html',
        path=current_app.config['SOCKET_PATH'],
        namespace=current_app.config['SOCKET_NAMESPACE'],
        messages=MESSAGES,
        **set_metadata_lists()
    )


# Bulk add sets
@add_page.route('/bulk', methods=['GET'])
@login_required
@exception_handler(__file__)
def bulk() -> str:
    BrickConfigurationList.error_unless_is_set('REBRICKABLE_API_KEY')

    return render_template(
        'add.html',
        path=current_app.config['SOCKET_PATH'],
        namespace=current_app.config['SOCKET_NAMESPACE'],
        messages=MESSAGES,
        bulk=True,
        **set_metadata_lists()
    )


# Add individual parts
@add_page.route('/parts', methods=['GET'])
@login_required
@exception_handler(__file__)
def parts() -> str:
    BrickConfigurationList.error_unless_is_set('REBRICKABLE_API_KEY')

    return render_template(
        'add_parts.html',
        path=current_app.config['SOCKET_PATH'],
        namespace=current_app.config['SOCKET_NAMESPACE'],
        messages=MESSAGES,
        **set_metadata_lists()
    )
