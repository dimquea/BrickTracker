from flask import Blueprint, current_app, render_template, request
from flask_login import login_required

from ..exceptions import exception_handler
from ...bricklink_catalog import error_unless_catalog
from ...rebrickable_set_list import RebrickableSetList
from ...socket import MESSAGES

admin_set_page = Blueprint('admin_set',  __name__, url_prefix='/admin/set')


# Sets that need to be refreshed
@admin_set_page.route('/refresh', methods=['GET'])
@login_required
@exception_handler(__file__)
def refresh() -> str:
    return render_template(
        'admin.html',
        refresh_set=True,
        table_collection=RebrickableSetList().need_refresh(),
        set_error=request.args.get('set_error')
    )


# Bulk refresh sets
@admin_set_page.route('/refresh/bulk', methods=['GET'])
@login_required
@exception_handler(__file__)
def refresh_bulk() -> str:
    error_unless_catalog()

    # Get list of sets needing refresh
    refresh_needed = RebrickableSetList().need_refresh()

    # Build comma-separated list of set numbers
    set_list = ', '.join([s.fields.set for s in refresh_needed.records])

    return render_template(
        'admin/set/refresh_bulk.html',
        path=current_app.config['SOCKET_PATH'],
        namespace=current_app.config['SOCKET_NAMESPACE'],
        messages=MESSAGES,
        bulk=True,
        refresh=True,
        set_list=set_list,
        refresh_count=len(refresh_needed.records)
    )
