from typing import Self

from .metadata_list import BrickMetadataList
from .set_tag import BrickSetTag


# Lego sets tag list
class BrickSetTagList(BrickMetadataList[BrickSetTag]):
    kind: str = 'set tags'

    # Database
    table: str = 'bricktracker_set_tags'
    order: str = '"bricktracker_metadata_tags"."name"'

    # Queries
    select_query: str = 'set/metadata/tag/list'

    # Endpoints
    set_state_endpoint: str = 'set.update_tag'

    # Instantiate the list with the proper class
    @classmethod
    def new(cls, /, *, force: bool = False) -> Self:
        return cls(BrickSetTag, force=force)
