from .metadata import BrickMetadata


# Lego set purchase location metadata
class BrickSetPurchaseLocation(BrickMetadata):
    kind: str = 'purchase location'

    # Endpoints
    individual_minifigure_value_endpoint: str = 'individual_minifigure.update_purchase_location'

    # Queries
    delete_query: str = 'set/metadata/purchase_location/delete'
    insert_query: str = 'set/metadata/purchase_location/insert'
    select_query: str = 'set/metadata/purchase_location/select'
    update_field_query: str = 'set/metadata/purchase_location/update/field'
    update_set_value_query: str = 'set/metadata/purchase_location/update/value'
    update_individual_minifigure_value_query: str = 'individual_minifigure/metadata/purchase_location/update/value'
