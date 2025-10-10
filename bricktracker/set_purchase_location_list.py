from typing import Self

from flask import current_app

from .metadata_list import BrickMetadataList
from .set_purchase_location import BrickSetPurchaseLocation


# Lego sets purchase location list
class BrickSetPurchaseLocationList(
    BrickMetadataList[BrickSetPurchaseLocation]
):
    kind: str = 'set purchase locations'

    # Order
    order: str = '"bricktracker_metadata_purchase_locations"."name"'

    # Queries
    select_query: str = 'set/metadata/purchase_location/list'
    all_query: str = 'set/metadata/purchase_location/all'

    # Set value endpoint
    set_value_endpoint: str = 'set.update_purchase_location'

    # Individual minifigure value endpoint
    individual_minifigure_value_endpoint: str = 'individual_minifigure.update_purchase_location'

    # Load all purchase locations
    @classmethod
    def all(cls, /) -> Self:
        new = cls.new()
        new.override()

        for record in new.select(
            override_query=cls.all_query,
            order=current_app.config['PURCHASE_LOCATION_DEFAULT_ORDER']
        ):
            new.records.append(new.model(record=record))

        return new

    # Instantiate the list with the proper class
    @classmethod
    def new(cls, /, *, force: bool = False) -> Self:
        return cls(BrickSetPurchaseLocation, force=force)
