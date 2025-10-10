from .metadata import BrickMetadata

from flask import url_for


# Lego set storage metadata
class BrickSetStorage(BrickMetadata):
    kind: str = 'storage'

    # Endpoints
    individual_minifigure_value_endpoint: str = 'individual_minifigure.update_storage'

    # Queries
    delete_query: str = 'set/metadata/storage/delete'
    insert_query: str = 'set/metadata/storage/insert'
    select_query: str = 'set/metadata/storage/select'
    update_field_query: str = 'set/metadata/storage/update/field'
    update_set_value_query: str = 'set/metadata/storage/update/value'
    update_individual_minifigure_value_query: str = 'individual_minifigure/metadata/storage/update/value'

    # Self url
    def url(self, /) -> str:
        return url_for(
            'storage.details',
            id=self.fields.id,
        )
