from typing import Self

from .metadata_list import BrickMetadataList
from .set_owner import BrickSetOwner


# Lego sets owner list
class BrickSetOwnerList(BrickMetadataList[BrickSetOwner]):
    kind: str = 'set owners'

    # Database
    table: str = 'bricktracker_set_owners'
    order: str = '"bricktracker_metadata_owners"."name"'

    # Queries
    select_query = 'set/metadata/owner/list'

    # Endpoints
    set_state_endpoint: str = 'set.update_owner'

    # Instantiate the list with the proper class
    @classmethod
    def new(cls, /, *, force: bool = False) -> Self:
        return cls(BrickSetOwner, force=force)
