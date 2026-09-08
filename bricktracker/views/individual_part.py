import logging
from functools import wraps

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required

from datetime import datetime

from .exceptions import exception_handler
from .upload import upload_helper
from ..bricklink_import import BrickLinkImport
from ..individual_part import IndividualPart
from ..individual_part_list import IndividualPartList
from ..individual_part_lot import IndividualPartLot
from ..individual_part_lot_list import IndividualPartLotList
from ..set_list import set_metadata_lists
from ..set_owner_list import BrickSetOwnerList
from ..set_tag_list import BrickSetTagList
from ..set_storage_list import BrickSetStorageList
from ..set_purchase_location_list import BrickSetPurchaseLocationList
from ..sql import BrickSQL

logger = logging.getLogger(__name__)

individual_part_page = Blueprint('individual_part', __name__, url_prefix='/individual-parts')


def require_individual_parts_write(f):
    """Decorator to block write operations (add/update/delete) when individual parts are disabled.
    This prevents adding new parts but allows viewing existing ones."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_app.config.get('DISABLE_INDIVIDUAL_PARTS', False):
            abort(404)
        return f(*args, **kwargs)
    return decorated_function


# List all individual parts
@individual_part_page.route('/')
@exception_handler(__file__)
def list() -> str:
    parts = IndividualPartList().all()

    writes_disabled = current_app.config.get('DISABLE_INDIVIDUAL_PARTS', False)

    return render_template(
        'individual_parts.html',
        parts=parts,
        writes_disabled=writes_disabled,
        **set_metadata_lists(as_class=True)
    )


# Import a BrickLink XML list of parts
@individual_part_page.route('/import', methods=['GET'])
@require_individual_parts_write
@login_required
@exception_handler(__file__)
def upload() -> str:
    return render_template(
        'individual_part/import.html',
        **set_metadata_lists(as_class=True),
    )


# Actually import the file
@individual_part_page.route('/import', methods=['POST'])
@require_individual_parts_write
@login_required
@exception_handler(__file__, post_redirect='individual_part.upload')
def do_upload() -> str | Response:
    file = upload_helper(
        'file',
        'individual_part.upload',
        extensions=['.xml'],
    )

    if isinstance(file, Response):
        return file

    imported = BrickLinkImport()
    imported.parse(file.read())

    # Лот заводится, только если его назвали: без имени партия ничем не
    # отличается от просто добавленных деталей
    lot = None
    name = request.form.get('lot_name', '').strip()

    if name:
        lot = {
            'name': name,
            'description': request.form.get('lot_description') or None,
            'storage': request.form.get('storage') or None,
            'purchase_location': request.form.get('purchase_location') or None,
            'purchase_date': parse_purchase_date(
                request.form.get('purchase_date'),
            ),
            'purchase_price': parse_purchase_price(
                request.form.get('purchase_price'),
            ),
        }

    added = imported.apply(lot=lot)

    # Отчёт показывается всегда, даже когда всё прошло: пропущенные
    # строки — единственный способ узнать, что часть файла не доехала
    return render_template(
        'individual_part/import.html',
        added=added,
        skipped=imported.skipped,
        done=True,
        **set_metadata_lists(as_class=True),
    )


# Дата и цена приходят из формы строками
def parse_purchase_date(value: str | None, /) -> float | None:
    if not value:
        return None

    try:
        return datetime.strptime(value, '%Y-%m-%d').timestamp()
    except ValueError:
        return None


def parse_purchase_price(value: str | None, /) -> float | None:
    if not value:
        return None

    try:
        return float(value)
    except ValueError:
        return None


# Quick add individual part from set parts table
@individual_part_page.route('/quick-add', methods=['POST'])
@exception_handler(__file__)
@require_individual_parts_write
@login_required
def quick_add() -> Response:
    """Quick add an individual part from a set's parts table"""
    import uuid

    data = request.get_json()

    # Validate required fields
    if not data or 'part' not in data or 'color' not in data:
        return jsonify({'error': 'Missing required fields: part and color'}), 400

    # Generate UUID for new individual part
    part_id = str(uuid.uuid4())

    # Extract fields with defaults
    quantity = data.get('quantity', 1)
    storage = data.get('storage') or None
    purchase_location = data.get('purchase_location') or None
    description = data.get('description') or None

    try:
        sql = BrickSQL()

        # Insert the individual part
        sql.execute(
            'individual_part/insert',
            parameters={
                'id': part_id,
                'part': data['part'],
                'color': data['color'],
                'quantity': quantity,
                'missing': 0,
                'damaged': 0,
                'checked': False,
                'description': description,
                'lot_id': None,  # Not part of a lot
                'storage': storage,
                'purchase_location': purchase_location,
                'purchase_date': None,
                'purchase_price': None
            }
        )

        # Initialize metadata rows (owners, tags, statuses) with default values
        # Uses the same SQL as updating set metadata, consolidated tables accept any entity id

        # Initialize owner metadata (all set to 0 initially)
        for owner in BrickSetOwnerList.list():
            sql.execute(
                'set/metadata/owner/update/state',
                parameters={
                    'set_id': part_id,
                    'state': 0
                },
                name=owner.as_column()
            )

        # Initialize tag metadata (all set to 0 initially)
        for tag in BrickSetTagList.list():
            sql.execute(
                'set/metadata/tag/update/state',
                parameters={
                    'set_id': part_id,
                    'state': 0
                },
                name=tag.as_column()
            )

        # Initialize status metadata (all set to 0 initially)
        # Note: Individual parts (not lots) support statuses
        from ..set_status_list import BrickSetStatusList
        for status in BrickSetStatusList.list():
            sql.execute(
                'set/metadata/status/update/state',
                parameters={
                    'set_id': part_id,
                    'state': 0
                },
                name=status.as_column()
            )

        sql.commit()

        logger.info('Quick-added individual part {id}: {part}/{color} x{quantity}'.format(
            id=part_id,
            part=data["part"],
            color=data["color"],
            quantity=quantity
        ))

        return jsonify({
            'success': True,
            'id': part_id,
            'message': 'Added {quantity}x {part} to individual parts inventory'.format(
                quantity=quantity,
                part=data["part"]
            )
        }), 201

    except Exception as e:
        logger.error('Error quick-adding individual part: {error}'.format(error=e))
        return jsonify({'error': str(e)}), 500


# Individual part instance details/edit
@individual_part_page.route('/<id>')
@exception_handler(__file__)
def details(*, id: str) -> str:
    item = IndividualPart().select_by_id(id)

    # Check if this part belongs to a lot
    lot = None
    if hasattr(item.fields, 'lot_id') and item.fields.lot_id:
        try:
            lot = IndividualPartLot().select_by_id(item.fields.lot_id)
        except Exception as e:
            logger.warning('Could not load lot {lot_id} for part {part_id}: {error}'.format(
                lot_id=item.fields.lot_id,
                part_id=id,
                error=e
            ))

    writes_disabled = current_app.config.get('DISABLE_INDIVIDUAL_PARTS', False)

    return render_template(
        'individual_part/details.html',
        item=item,
        lot=lot,
        writes_disabled=writes_disabled,
        **set_metadata_lists(as_class=True)
    )


# Update individual part instance
@individual_part_page.route('/<id>/update', methods=['POST'])
@exception_handler(__file__)
@require_individual_parts_write
def update(*, id: str):
    item = IndividualPart().select_by_id(id)

    # Update basic fields
    item.fields.quantity = int(request.form.get('quantity', 1))
    item.fields.description = request.form.get('description', '')
    item.fields.storage = request.form.get('storage') or None
    item.fields.purchase_location = request.form.get('purchase_location') or None
    item.fields.purchase_date = request.form.get('purchase_date') or None
    item.fields.purchase_price = request.form.get('purchase_price') or None

    # Update the individual part
    BrickSQL().execute(
        'individual_part/update_full',
        parameters={
            'id': item.fields.id,
            'quantity': item.fields.quantity,
            'description': item.fields.description,
            'storage': item.fields.storage,
            'purchase_location': item.fields.purchase_location,
            'purchase_date': item.fields.purchase_date,
            'purchase_price': item.fields.purchase_price,
        },
        commit=False,
    )

    # Update owners
    owners = request.form.getlist('owners')
    for owner in BrickSetOwnerList.list():
        owner.update_individual_part_state(item, state=(owner.fields.id in owners))

    # Update tags
    tags = request.form.getlist('tags')
    for tag in BrickSetTagList.list():
        tag.update_individual_part_state(item, state=(tag.fields.id in tags))

    BrickSQL().commit()

    return redirect(url_for('individual_part.details', id=id))


# Update quantity
@individual_part_page.route('/<id>/update/quantity', methods=['POST'])
@exception_handler(__file__)
@require_individual_parts_write
@login_required
def update_quantity(*, id: str):
    item = IndividualPart().select_by_id(id)
    value = request.json.get('value', '1')

    # Handle empty string or 0 - don't allow it
    if value == '' or value == '0' or value == 0:
        return jsonify({'success': False, 'error': 'Quantity cannot be 0. Use the delete button in the menu to remove this part from the lot.'})

    try:
        quantity = int(value)
        if quantity < 1:
            return jsonify({'success': False, 'error': 'Quantity must be at least 1'})
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid quantity value'})

    item.update_field('quantity', quantity)
    return jsonify({'success': True})


# Update description
@individual_part_page.route('/<id>/update/description', methods=['POST'])
@exception_handler(__file__)
@require_individual_parts_write
@login_required
def update_description(*, id: str):
    item = IndividualPart().select_by_id(id)
    description = request.json.get('value', '')
    item.update_field('description', description)
    return jsonify({'success': True})


# Update purchase date
@individual_part_page.route('/<id>/update/purchase_date', methods=['POST'])
@exception_handler(__file__)
@require_individual_parts_write
@login_required
def update_purchase_date(*, id: str):
    item = IndividualPart().select_by_id(id)
    purchase_date = request.json.get('value', '')

    # Convert date string to timestamp if provided, otherwise None
    if purchase_date and purchase_date.strip():
        try:
            from datetime import datetime
            # Expecting yyyy/mm/dd format
            date_obj = datetime.strptime(purchase_date, '%Y/%m/%d')
            timestamp = date_obj.timestamp()
            item.update_field('purchase_date', timestamp)
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid date format. Expected yyyy/mm/dd'})
    else:
        item.update_field('purchase_date', None)

    return jsonify({'success': True})


# Update purchase price
@individual_part_page.route('/<id>/update/purchase_price', methods=['POST'])
@exception_handler(__file__)
@require_individual_parts_write
@login_required
def update_purchase_price(*, id: str):
    item = IndividualPart().select_by_id(id)
    purchase_price = request.json.get('value', '')

    # Convert to float if provided, otherwise None
    if purchase_price is not None and str(purchase_price).strip() != '':
        try:
            price = float(purchase_price)
            item.update_field('purchase_price', price)
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid price value'})
    else:
        item.update_field('purchase_price', None)

    return jsonify({'success': True})


# Update owner
@individual_part_page.route('/<id>/update/owner/<metadata_id>', methods=['POST'])
@exception_handler(__file__)
@require_individual_parts_write
@login_required
def update_owner(*, id: str, metadata_id: str):
    item = IndividualPart().select_by_id(id)
    owner = BrickSetOwnerList.get(metadata_id)
    owner.update_individual_part_state(item, json=request.json)
    return jsonify({'success': True})


# Update tag
@individual_part_page.route('/<id>/update/tag/<metadata_id>', methods=['POST'])
@exception_handler(__file__)
@require_individual_parts_write
@login_required
def update_tag(*, id: str, metadata_id: str):
    item = IndividualPart().select_by_id(id)
    tag = BrickSetTagList.get(metadata_id)
    tag.update_individual_part_state(item, json=request.json)
    return jsonify({'success': True})


# Update status
@individual_part_page.route('/<id>/update/status/<metadata_id>', methods=['POST'])
@exception_handler(__file__)
@require_individual_parts_write
@login_required
def update_status(*, id: str, metadata_id: str):
    item = IndividualPart().select_by_id(id)
    from ..set_status_list import BrickSetStatusList
    status = BrickSetStatusList.get(metadata_id)
    status.update_individual_part_state(item, json=request.json)
    return jsonify({'success': True})


# Update storage
@individual_part_page.route('/<id>/update/storage', methods=['POST'])
@exception_handler(__file__)
@require_individual_parts_write
@login_required
def update_storage(*, id: str):
    item = IndividualPart().select_by_id(id)
    storage_id = request.json.get('value')
    item.update_field('storage', storage_id if storage_id else None)
    return jsonify({'success': True})


# Update purchase location
@individual_part_page.route('/<id>/update/purchase_location', methods=['POST'])
@exception_handler(__file__)
@require_individual_parts_write
@login_required
def update_purchase_location(*, id: str):
    item = IndividualPart().select_by_id(id)
    location_id = request.json.get('value')
    item.update_field('purchase_location', location_id if location_id else None)
    return jsonify({'success': True})


# Update missing count
@individual_part_page.route('/<id>/update/missing', methods=['POST'])
@exception_handler(__file__)
@require_individual_parts_write
@login_required
def update_missing(*, id: str):
    item = IndividualPart().select_by_id(id)
    amount = item.update_problem('missing', request.json)

    logger.info('Individual part {part} (color: {color}, id: {id}): updated missing count to {amount}'.format(
        part=item.fields.part,
        color=item.fields.color,
        id=item.fields.id,
        amount=amount
    ))

    return jsonify({'missing': amount})


# Update damaged count
@individual_part_page.route('/<id>/update/damaged', methods=['POST'])
@exception_handler(__file__)
@require_individual_parts_write
@login_required
def update_damaged(*, id: str):
    item = IndividualPart().select_by_id(id)
    amount = item.update_problem('damaged', request.json)

    logger.info('Individual part {part} (color: {color}, id: {id}): updated damaged count to {amount}'.format(
        part=item.fields.part,
        color=item.fields.color,
        id=item.fields.id,
        amount=amount
    ))

    return jsonify({'damaged': amount})


# Update checked state
@individual_part_page.route('/<id>/update/checked', methods=['POST'])
@exception_handler(__file__)
@require_individual_parts_write
@login_required
def update_checked(*, id: str):
    item = IndividualPart().select_by_id(id)
    checked = item.update_checked(request.json)

    logger.info('Individual part {part} (color: {color}, id: {id}): updated checked state to {checked}'.format(
        part=item.fields.part,
        color=item.fields.color,
        id=item.fields.id,
        checked=checked
    ))

    return jsonify({'checked': checked})


# Delete individual part instance
@individual_part_page.route('/<id>/delete', methods=['POST'])
@exception_handler(__file__)
@require_individual_parts_write
@login_required
def delete_part(*, id: str):
    item = IndividualPart().select_by_id(id)
    lot_id = item.fields.lot_id if hasattr(item.fields, 'lot_id') else None

    item.delete()

    logger.info('Deleted individual part {part} (color: {color}, id: {id})'.format(
        part=item.fields.part,
        color=item.fields.color,
        id=id
    ))

    # If part was in a lot, redirect back to the lot
    if lot_id:
        return redirect(url_for('individual_part.lot_details', lot_id=lot_id))
    else:
        return redirect(url_for('individual_part.list'))


# List all lots
@individual_part_page.route('/lot/')
@exception_handler(__file__)
def list_lots() -> str:
    """List all individual part lots"""
    # Use optimized query that includes part_count
    lots = IndividualPartLotList().all()

    return render_template(
        'individual_part/lots.html',
        lots=lots,
        **set_metadata_lists(as_class=True)
    )


# Lot detail page
@individual_part_page.route('/lot/<lot_id>')
@exception_handler(__file__)
def lot_details(*, lot_id: str) -> str:
    """Display details for an individual part lot (behaves like a set)"""
    lot = IndividualPartLot().select_by_id(lot_id)

    writes_disabled = current_app.config.get('DISABLE_INDIVIDUAL_PARTS', False)

    return render_template(
        'individual_part/lot_details.html',
        item=lot,  # Pass as 'item' like sets do
        solo=True,
        writes_disabled=writes_disabled,
        **set_metadata_lists(as_class=True)
    )


# Update lot name
@individual_part_page.route('/lot/<lot_id>/update/name', methods=['POST'])
@exception_handler(__file__)
@require_individual_parts_write
@login_required
def update_lot_name(*, lot_id: str):
    lot = IndividualPartLot().select_by_id(lot_id)
    name = request.json.get('value', '')

    from ..sql import BrickSQL
    sql = BrickSQL()
    sql.execute_and_commit('individual_part_lot/update/name', parameters={'name': name, 'id': lot_id})

    logger.info('Updated lot {lot_id} name to: {name}'.format(lot_id=lot_id, name=name))

    return jsonify({'success': True})


# Update lot description
@individual_part_page.route('/lot/<lot_id>/update/description', methods=['POST'])
@exception_handler(__file__)
@require_individual_parts_write
@login_required
def update_lot_description(*, lot_id: str):
    lot = IndividualPartLot().select_by_id(lot_id)
    description = request.json.get('value', '')

    from ..sql import BrickSQL
    sql = BrickSQL()
    sql.execute_and_commit('individual_part_lot/update/description', parameters={'description': description, 'id': lot_id})

    logger.info('Updated lot {lot_id} description'.format(lot_id=lot_id))

    return jsonify({'success': True})


# Delete lot
@individual_part_page.route('/lot/<lot_id>/delete', methods=['POST'])
@exception_handler(__file__)
@require_individual_parts_write
@login_required
def delete_lot(*, lot_id: str):
    lot = IndividualPartLot().select_by_id(lot_id)
    lot.delete()

    logger.info('Deleted individual part lot {lot_id}'.format(lot_id=lot_id))

    return redirect(url_for('individual_part.list_lots'))


# Update lot owner
@individual_part_page.route('/lot/<lot_id>/update/owner/<metadata_id>', methods=['POST'])
@exception_handler(__file__)
@require_individual_parts_write
@login_required
def update_lot_owner(*, lot_id: str, metadata_id: str):
    from ..set_owner_list import BrickSetOwnerList
    lot = IndividualPartLot().select_by_id(lot_id)
    owner = BrickSetOwnerList.get(metadata_id)
    owner.update_individual_part_lot_state(lot, json=request.json)
    return jsonify({'success': True})


# Update lot tag
@individual_part_page.route('/lot/<lot_id>/update/tag/<metadata_id>', methods=['POST'])
@exception_handler(__file__)
@require_individual_parts_write
@login_required
def update_lot_tag(*, lot_id: str, metadata_id: str):
    from ..set_tag_list import BrickSetTagList
    lot = IndividualPartLot().select_by_id(lot_id)
    tag = BrickSetTagList.get(metadata_id)
    tag.update_individual_part_lot_state(lot, json=request.json)
    return jsonify({'success': True})


# Update lot status
@individual_part_page.route('/lot/<lot_id>/update/status/<metadata_id>', methods=['POST'])
@exception_handler(__file__)
@require_individual_parts_write
@login_required
def update_lot_status(*, lot_id: str, metadata_id: str):
    from ..set_status_list import BrickSetStatusList
    lot = IndividualPartLot().select_by_id(lot_id)
    status = BrickSetStatusList.get(metadata_id)
    status.update_individual_part_lot_state(lot, json=request.json)
    return jsonify({'success': True})


# Update lot storage
@individual_part_page.route('/lot/<lot_id>/update/storage', methods=['POST'])
@exception_handler(__file__)
@require_individual_parts_write
@login_required
def update_lot_storage(*, lot_id: str):
    from ..set_storage_list import BrickSetStorageList
    lot = IndividualPartLot().select_by_id(lot_id)
    storage_id = request.json.get('value', '')

    from ..sql import BrickSQL
    sql = BrickSQL()
    sql.execute_and_commit('individual_part_lot/update/storage', parameters={'storage': storage_id if storage_id else None, 'id': lot_id})

    logger.info('Updated lot {lot_id} storage to: {storage}'.format(lot_id=lot_id, storage=storage_id))
    return jsonify({'success': True})


# Update lot purchase location
@individual_part_page.route('/lot/<lot_id>/update/purchase_location', methods=['POST'])
@exception_handler(__file__)
@require_individual_parts_write
@login_required
def update_lot_purchase_location(*, lot_id: str):
    from ..set_purchase_location_list import BrickSetPurchaseLocationList
    lot = IndividualPartLot().select_by_id(lot_id)
    location_id = request.json.get('value', '')

    from ..sql import BrickSQL
    sql = BrickSQL()
    sql.execute_and_commit('individual_part_lot/update/purchase_location', parameters={'purchase_location': location_id if location_id else None, 'id': lot_id})

    logger.info('Updated lot {lot_id} purchase_location to: {location}'.format(lot_id=lot_id, location=location_id))
    return jsonify({'success': True})


# Update lot purchase date
@individual_part_page.route('/lot/<lot_id>/update/purchase_date', methods=['POST'])
@exception_handler(__file__)
@require_individual_parts_write
@login_required
def update_lot_purchase_date(*, lot_id: str):
    from datetime import datetime

    lot = IndividualPartLot().select_by_id(lot_id)
    purchase_date_str = request.json.get('value')

    # Convert date string to Unix timestamp (same as sets)
    purchase_date = None
    if purchase_date_str and purchase_date_str != '':
        try:
            purchase_date = datetime.strptime(purchase_date_str, '%Y/%m/%d').timestamp()
        except ValueError as e:
            logger.error('Invalid date format: {date}'.format(date=purchase_date_str))
            return jsonify({'error': '{date} is not a valid date'.format(date=purchase_date_str)}), 400

    from ..sql import BrickSQL
    sql = BrickSQL()
    sql.execute_and_commit('individual_part_lot/update/purchase_date', parameters={'purchase_date': purchase_date, 'id': lot_id})

    logger.info('Updated lot {lot_id} purchase_date to: {date}'.format(lot_id=lot_id, date=purchase_date))
    return jsonify({'success': True})


# Update lot purchase price
@individual_part_page.route('/lot/<lot_id>/update/purchase_price', methods=['POST'])
@exception_handler(__file__)
@require_individual_parts_write
@login_required
def update_lot_purchase_price(*, lot_id: str):
    lot = IndividualPartLot().select_by_id(lot_id)
    purchase_price = request.json.get('value')

    from ..sql import BrickSQL
    sql = BrickSQL()
    if purchase_price is not None and str(purchase_price).strip() != '':
        try:
            purchase_price = float(purchase_price)
        except (ValueError, TypeError):
            purchase_price = None
    else:
        purchase_price = None
    sql.execute_and_commit('individual_part_lot/update/purchase_price', parameters={'purchase_price': purchase_price, 'id': lot_id})

    logger.info('Updated lot {lot_id} purchase_price to: {price}'.format(lot_id=lot_id, price=purchase_price))
    return jsonify({'success': True})
