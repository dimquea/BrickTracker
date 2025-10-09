from .metadata import BrickMetadata


# Lego set owner metadata
class BrickSetOwner(BrickMetadata):
    kind: str = 'owner'

    # Set state endpoint
    set_state_endpoint: str = 'set.update_owner'

    # Queries
    delete_query: str = 'set/metadata/owner/delete'
    insert_query: str = 'set/metadata/owner/insert'
    select_query: str = 'set/metadata/owner/select'
    update_field_query: str = 'set/metadata/owner/update/field'
    update_set_state_query: str = 'set/metadata/owner/update/state'
    update_individual_minifigure_state_query: str = 'individual_minifigure/metadata/owner/update/state'
