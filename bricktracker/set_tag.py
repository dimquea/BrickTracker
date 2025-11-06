from .metadata import BrickMetadata


# Lego set tag metadata
class BrickSetTag(BrickMetadata):
    kind: str = 'tag'

    # Endpoints
    set_state_endpoint: str = 'set.update_tag'
    individual_minifigure_state_endpoint: str = 'individual_minifigure.update_tag'
    individual_part_state_endpoint: str = 'individual_part.update_tag'

    # Queries
    delete_query: str = 'set/metadata/tag/delete'
    insert_query: str = 'set/metadata/tag/insert'
    select_query: str = 'set/metadata/tag/select'
    update_field_query: str = 'set/metadata/tag/update/field'
    update_set_state_query: str = 'set/metadata/tag/update/state'
    update_individual_minifigure_state_query: str = 'individual_minifigure/metadata/tag/update/state'
    update_individual_part_state_query: str = 'individual_part/metadata/tag/update/state'
