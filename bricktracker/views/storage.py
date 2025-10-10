from flask import Blueprint, render_template

from .exceptions import exception_handler
from ..individual_minifigure_list import IndividualMinifigureList
from ..set_list import BrickSetList, set_metadata_lists
from ..set_storage import BrickSetStorage
from ..set_storage_list import BrickSetStorageList
from ..sql import BrickSQL

storage_page = Blueprint('storage', __name__, url_prefix='/storages')


# Index
@storage_page.route('/', methods=['GET'])
@exception_handler(__file__)
def list() -> str:
    # Get counts of items with no storage
    sql = BrickSQL()

    # Count sets with no storage
    sets_no_storage_query = 'SELECT COUNT(*) FROM "bricktracker_sets" WHERE "storage" IS NULL'
    sql.cursor.execute(sets_no_storage_query)
    sets_no_storage = sql.cursor.fetchone()[0]

    # Count individual minifigures with no storage
    minifigs_no_storage_query = 'SELECT COUNT(*) FROM "bricktracker_individual_minifigures" WHERE "storage" IS NULL'
    sql.cursor.execute(minifigs_no_storage_query)
    minifigs_no_storage = sql.cursor.fetchone()[0]

    return render_template(
        'storages.html',
        table_collection=BrickSetStorageList.all(),
        sets_no_storage=sets_no_storage,
        minifigs_no_storage=minifigs_no_storage,
    )


# Storage details - no storage
@storage_page.route('/no_storage/details')
@exception_handler(__file__)
def no_storage_details() -> str:
    # Create a mock storage object for "no storage"
    from ..record import BrickRecord

    no_storage = BrickRecord()
    no_storage.fields.id = None
    no_storage.fields.name = 'Not in a storage location'

    # Get sets and individual minifigures with no storage
    sets = BrickSetList().without_storage()
    individual_minifigures = IndividualMinifigureList().without_storage()

    return render_template(
        'storage.html',
        item=no_storage,
        sets=sets,
        individual_minifigures=individual_minifigures,
        **set_metadata_lists(as_class=True)
    )


# Storage details
@storage_page.route('/<id>/details')
@exception_handler(__file__)
def details(*, id: str) -> str:
    storage = BrickSetStorage().select_specific(id)

    return render_template(
        'storage.html',
        item=storage,
        sets=BrickSetList().using_storage(storage),
        individual_minifigures=IndividualMinifigureList().using_storage(storage),
        **set_metadata_lists(as_class=True)
    )
