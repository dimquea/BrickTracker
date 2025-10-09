from flask import Blueprint, redirect, render_template, request, url_for

from .exceptions import exception_handler
from ..individual_minifigure import IndividualMinifigure
from ..set_list import set_metadata_lists
from ..set_owner_list import BrickSetOwnerList
from ..set_tag_list import BrickSetTagList

individual_minifigure_page = Blueprint('individual_minifigure', __name__, url_prefix='/individual-minifigures')


# Individual minifigure instance details/edit
@individual_minifigure_page.route('/<id>')
@exception_handler(__file__)
def details(*, id: str) -> str:
    item = IndividualMinifigure().select_by_id(id)

    return render_template(
        'individual_minifigure/details.html',
        item=item,
        **set_metadata_lists(as_class=True)
    )


# Update individual minifigure instance
@individual_minifigure_page.route('/<id>/update', methods=['POST'])
@exception_handler(__file__)
def update(*, id: str):
    item = IndividualMinifigure().select_by_id(id)

    # Update basic fields
    item.fields.quantity = int(request.form.get('quantity', 1))
    item.fields.description = request.form.get('description', '')
    item.fields.storage = request.form.get('storage') or None
    item.fields.purchase_location = request.form.get('purchase_location') or None

    # Update the individual minifigure
    from ..sql import BrickSQL
    BrickSQL().execute(
        'individual_minifigure/update',
        parameters={
            'id': item.fields.id,
            'quantity': item.fields.quantity,
            'description': item.fields.description,
            'storage': item.fields.storage,
            'purchase_location': item.fields.purchase_location,
        },
        commit=False,
    )

    # Update owners
    owners = request.form.getlist('owners')
    for owner in BrickSetOwnerList.list():
        owner.update_individual_minifigure_state(item, state=(owner.fields.id in owners))

    # Update tags
    tags = request.form.getlist('tags')
    for tag in BrickSetTagList.list():
        tag.update_individual_minifigure_state(item, state=(tag.fields.id in tags))

    BrickSQL().commit()

    return redirect(url_for('individual_minifigure.details', id=id))


# Delete individual minifigure instance
@individual_minifigure_page.route('/<id>/delete', methods=['POST'])
@exception_handler(__file__)
def delete(*, id: str):
    item = IndividualMinifigure().select_by_id(id)
    figure = item.fields.figure
    item.delete()

    return redirect(url_for('minifigure.details', figure=figure))
