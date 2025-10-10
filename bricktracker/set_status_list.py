from typing import Self

from .metadata_list import BrickMetadataList
from .set_status import BrickSetStatus


# Lego sets status list
class BrickSetStatusList(BrickMetadataList[BrickSetStatus]):
    kind: str = 'set statuses'

    # Database
    table: str = 'bricktracker_set_statuses'
    order: str = '"bricktracker_metadata_statuses"."name"'

    # Queries
    select_query = 'set/metadata/status/list'

    # Endpoints
    set_state_endpoint: str = 'set.update_status'

    # Filter the list of set status
    def filter(self, all: bool = False) -> list[BrickSetStatus]:
        return [
            record
            for record
            in self.records
            if all or record.fields.displayed_on_grid
        ]

    # Instantiate the list with the proper class
    @classmethod
    def new(cls, /, *, force: bool = False) -> Self:
        return cls(BrickSetStatus, force=force)
