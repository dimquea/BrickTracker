import logging
from typing import List, overload, Self, Type, TypeVar

from flask import url_for

from .exceptions import ErrorException, NotFoundException
from .fields import BrickRecordFields
from .record_list import BrickRecordList
from .set_owner import BrickSetOwner
from .set_purchase_location import BrickSetPurchaseLocation
from .set_status import BrickSetStatus
from .set_storage import BrickSetStorage
from .set_tag import BrickSetTag
from .wish_owner import BrickWishOwner

logger = logging.getLogger(__name__)

T = TypeVar(
    'T',
    BrickSetOwner,
    BrickSetPurchaseLocation,
    BrickSetStatus,
    BrickSetStorage,
    BrickSetTag,
    BrickWishOwner
)


# Lego sets metadata list
class BrickMetadataList(BrickRecordList[T]):
    kind: str
    mapping: dict[str, T]
    model: Type[T]

    # Database
    table: str
    order: str

    # Queries
    select_query: str

    # List-specific endpoints (for operations on the list itself)
    set_state_endpoint: str = ''
    set_value_endpoint: str = ''
    individual_minifigure_value_endpoint: str = ''

    def __init__(
        self,
        model: Type[T],
        /,
        *,
        force: bool = False,
        records: list[T] | None = None
    ):
        self.model = model

        # Records override (masking the class variables with instance ones)
        if records is not None:
            self.override()

            for metadata in records:
                self.records.append(metadata)
                self.mapping[metadata.fields.id] = metadata
        else:
            # Load metadata only if there is none already loaded
            records = getattr(self, 'records', None)

            if records is None or force:
                # Don't use super()__init__ as it would mask class variables
                self.fields = BrickRecordFields()

                logger.info('Loading {kind} list'.format(
                    kind=self.kind
                ))

                self.__class__.records = []
                self.__class__.mapping = {}

                # Load the metadata from the database
                for record in self.select(order=self.order):
                    metadata = model(record=record)

                    self.__class__.records.append(metadata)
                    self.__class__.mapping[metadata.fields.id] = metadata

    # HTML prefix name
    def as_prefix(self, /) -> str:
        return self.kind.replace(' ', '-')

    # Filter the list of records (this one does nothing)
    def filter(self) -> list[T]:
        return self.records

    # Add a layer of override data
    def override(self) -> None:
        self.fields = BrickRecordFields()

        self.records = []
        self.mapping = {}

    # Return the items as columns for a select
    @classmethod
    def as_columns(cls, /, table: str | None = None, **kwargs) -> str:
        new = cls.new()

        # Use provided table name or default to class table
        table_name = table if table is not None else cls.table

        return ', '.join([
            '"{table}"."{column}"'.format(
                table=table_name,
                column=record.as_column(),
            )
            for record
            in new.filter(**kwargs)
        ])

    # Return the items as a dictionary mapping column names to UUIDs
    @classmethod
    def as_column_mapping(cls, /, **kwargs) -> dict:
        new = cls.new()

        return {
            record.as_column(): record.fields.id
            for record in new.filter(**kwargs)
        }

    # Grab a specific status
    @classmethod
    def get(cls, id: str | None, /, *, allow_none: bool = False) -> T:
        new = cls.new()

        if allow_none and (id == '' or id is None):
            return new.model()

        if id is None:
            raise ErrorException('Cannot get {kind} with no ID'.format(
                kind=new.kind.capitalize()
            ))

        if id not in new.mapping:
            raise NotFoundException(
                '{kind} with ID {id} was not found in the database'.format(
                    kind=new.kind.capitalize(),
                    id=id,
                ),
            )

        return new.mapping[id]

    # Get the list of statuses depending on the context
    @overload
    @classmethod
    def list(cls, /, **kwargs) -> List[T]: ...

    @overload
    @classmethod
    def list(cls, /, as_class: bool = False, **kwargs) -> Self: ...

    @classmethod
    def list(cls, /, as_class: bool = False, **kwargs) -> List[T] | Self:
        new = cls.new()
        list = new.filter(**kwargs)

        if as_class:
            # Return a copy of the metadata list with overriden records
            return cls(new.model, records=list)
        else:
            return list

    # Instantiate the list with the proper class
    @classmethod
    def new(cls, /, *, force: bool = False) -> Self:
        raise Exception('new() is not implemented for BrickMetadataList')

    # URL to change the selected state of this metadata item for a set
    @classmethod
    def url_for_set_state(cls, id: str, /) -> str:
        return url_for(
            cls.set_state_endpoint,
            id=id,
        )

    # URL to change the selected value of this metadata item for a set
    @classmethod
    def url_for_set_value(cls, id: str, /) -> str:
        return url_for(
            cls.set_value_endpoint,
            id=id,
        )

    # URL to change the selected value of this metadata item for an individual minifigure
    @classmethod
    def url_for_individual_minifigure_value(cls, id: str, /) -> str:
        return url_for(
            cls.individual_minifigure_value_endpoint,
            id=id,
        )
