from typing import Self

from flask import current_app

from .metadata_list import BrickMetadataList
from .set_storage import BrickSetStorage


# Lego sets storage list
class BrickSetStorageList(BrickMetadataList[BrickSetStorage]):
    kind: str = 'set storages'

    # Order
    order: str = '"bricktracker_metadata_storages"."name"'

    # Queries
    select_query: str = 'set/metadata/storage/list'
    all_query: str = 'set/metadata/storage/all'

    # Set value endpoint
    set_value_endpoint: str = 'set.update_storage'

    # Individual minifigure value endpoint
    individual_minifigure_value_endpoint: str = 'individual_minifigure.update_storage'

    # Load all storages
    @classmethod
    def all(cls, /) -> Self:
        new = cls.new()
        new.override()

        for record in new.select(
            override_query=cls.all_query,
            order=current_app.config['STORAGE_DEFAULT_ORDER']
        ):
            new.records.append(new.model(record=record))

        return new

    # Instantiate the list with the proper class
    @classmethod
    def new(cls, /, *, force: bool = False) -> Self:
        return cls(BrickSetStorage, force=force)
