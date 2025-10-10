from flask import Blueprint, render_template

from .exceptions import exception_handler
from ..minifigure_list import BrickMinifigureList
from ..set_list import BrickSetList, set_metadata_lists

index_page = Blueprint('index', __name__)


# Index
@index_page.route('/', methods=['GET'])
@exception_handler(__file__)
def index() -> str:
    return render_template(
        'index.html',
        brickset_collection=BrickSetList().last(),
        minifigure_collection=BrickMinifigureList().last(),
        **set_metadata_lists(as_class=True)
    )
