import logging

from flask import Blueprint, jsonify, redirect, render_template, request, url_for, Response
from flask_login import login_required

from .exceptions import exception_handler
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


# List all individual parts
@individual_part_page.route('/')
@exception_handler(__file__)
def list_all() -> str:
    parts = IndividualPartList().all()

    return render_template(
        'individual_parts.html',
        parts=parts,
        **set_metadata_lists(as_class=True)
    )


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
            logger.warning(f'Could not load lot {item.fields.lot_id} for part {id}: {e}')

    return render_template(
        'individual_part/details.html',
        item=item,
        lot=lot,
        **set_metadata_lists(as_class=True)
    )


# Update individual part instance
@individual_part_page.route('/<id>/update', methods=['POST'])
@exception_handler(__file__)
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
@login_required
@exception_handler(__file__)
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
@login_required
@exception_handler(__file__)
def update_description(*, id: str):
    item = IndividualPart().select_by_id(id)
    description = request.json.get('value', '')
    item.update_field('description', description)
    return jsonify({'success': True})


# Update owner
@individual_part_page.route('/<id>/update/owner/<metadata_id>', methods=['POST'])
@login_required
@exception_handler(__file__)
def update_owner(*, id: str, metadata_id: str):
    item = IndividualPart().select_by_id(id)
    owner = BrickSetOwnerList.get(metadata_id)
    owner.update_individual_part_state(item, json=request.json)
    return jsonify({'success': True})


# Update tag
@individual_part_page.route('/<id>/update/tag/<metadata_id>', methods=['POST'])
@login_required
@exception_handler(__file__)
def update_tag(*, id: str, metadata_id: str):
    item = IndividualPart().select_by_id(id)
    tag = BrickSetTagList.get(metadata_id)
    tag.update_individual_part_state(item, json=request.json)
    return jsonify({'success': True})


# Update status
@individual_part_page.route('/<id>/update/status/<metadata_id>', methods=['POST'])
@login_required
@exception_handler(__file__)
def update_status(*, id: str, metadata_id: str):
    item = IndividualPart().select_by_id(id)
    from ..set_status_list import BrickSetStatusList
    status = BrickSetStatusList.get(metadata_id)
    status.update_individual_part_state(item, json=request.json)
    return jsonify({'success': True})


# Update storage
@individual_part_page.route('/<id>/update/storage', methods=['POST'])
@login_required
@exception_handler(__file__)
def update_storage(*, id: str):
    item = IndividualPart().select_by_id(id)
    storage_id = request.json.get('value')
    item.update_field('storage', storage_id if storage_id else None)
    return jsonify({'success': True})


# Update purchase location
@individual_part_page.route('/<id>/update/purchase_location', methods=['POST'])
@login_required
@exception_handler(__file__)
def update_purchase_location(*, id: str):
    item = IndividualPart().select_by_id(id)
    location_id = request.json.get('value')
    item.update_field('purchase_location', location_id if location_id else None)
    return jsonify({'success': True})


# Update missing count
@individual_part_page.route('/<id>/update/missing', methods=['POST'])
@login_required
@exception_handler(__file__)
def update_missing(*, id: str):
    item = IndividualPart().select_by_id(id)
    amount = item.update_problem('missing', request.json)

    logger.info(f'Individual part {item.fields.part} (color: {item.fields.color}, id: {item.fields.id}): updated missing count to {amount}')

    return jsonify({'missing': amount})


# Update damaged count
@individual_part_page.route('/<id>/update/damaged', methods=['POST'])
@login_required
@exception_handler(__file__)
def update_damaged(*, id: str):
    item = IndividualPart().select_by_id(id)
    amount = item.update_problem('damaged', request.json)

    logger.info(f'Individual part {item.fields.part} (color: {item.fields.color}, id: {item.fields.id}): updated damaged count to {amount}')

    return jsonify({'damaged': amount})


# Update checked state
@individual_part_page.route('/<id>/update/checked', methods=['POST'])
@login_required
@exception_handler(__file__)
def update_checked(*, id: str):
    item = IndividualPart().select_by_id(id)
    checked = item.update_checked(request.json)

    logger.info(f'Individual part {item.fields.part} (color: {item.fields.color}, id: {item.fields.id}): updated checked state to {checked}')

    return jsonify({'checked': checked})


# Delete individual part instance
@individual_part_page.route('/<id>/delete', methods=['POST'])
@login_required
@exception_handler(__file__)
def delete_part(*, id: str):
    item = IndividualPart().select_by_id(id)
    lot_id = item.fields.lot_id if hasattr(item.fields, 'lot_id') else None

    item.delete()

    logger.info(f'Deleted individual part {item.fields.part} (color: {item.fields.color}, id: {id})')

    # If part was in a lot, redirect back to the lot
    if lot_id:
        return redirect(url_for('individual_part.lot_details', lot_id=lot_id))
    else:
        return redirect(url_for('individual_part.list_all'))


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

    return render_template(
        'individual_part/lot_details.html',
        item=lot,  # Pass as 'item' like sets do
        solo=True,
        **set_metadata_lists(as_class=True)
    )


# Update lot name
@individual_part_page.route('/lot/<lot_id>/update/name', methods=['POST'])
@login_required
@exception_handler(__file__)
def update_lot_name(*, lot_id: str):
    lot = IndividualPartLot().select_by_id(lot_id)
    name = request.json.get('value', '')

    from ..sql import BrickSQL
    sql = BrickSQL()
    sql.cursor.execute(
        'UPDATE "bricktracker_individual_part_lots" SET "name" = ? WHERE "id" = ?',
        (name, lot_id)
    )
    sql.commit()

    logger.info(f'Updated lot {lot_id} name to: {name}')

    return jsonify({'success': True})


# Update lot description
@individual_part_page.route('/lot/<lot_id>/update/description', methods=['POST'])
@login_required
@exception_handler(__file__)
def update_lot_description(*, lot_id: str):
    lot = IndividualPartLot().select_by_id(lot_id)
    description = request.json.get('value', '')

    from ..sql import BrickSQL
    sql = BrickSQL()
    sql.cursor.execute(
        'UPDATE "bricktracker_individual_part_lots" SET "description" = ? WHERE "id" = ?',
        (description, lot_id)
    )
    sql.commit()

    logger.info(f'Updated lot {lot_id} description')

    return jsonify({'success': True})


# Delete lot
@individual_part_page.route('/lot/<lot_id>/delete', methods=['POST'])
@login_required
@exception_handler(__file__)
def delete_lot(*, lot_id: str):
    lot = IndividualPartLot().select_by_id(lot_id)
    lot.delete()

    logger.info(f'Deleted individual part lot {lot_id}')

    return redirect(url_for('individual_part.list_lots'))
