from datetime import datetime
from sqlite3 import Row
from typing import Any, ItemsView

from .fields import BrickRecordFields
from .sql import BrickSQL


def format_timestamp(timestamp: float | None, format_key: str = 'PURCHASE_DATE_FORMAT') -> str:
    """
    Format a timestamp for display.

    Args:
        timestamp: Unix timestamp (float) or None
        format_key: Config key for date format string

    Returns:
        Formatted date string or empty string if timestamp is None
    """
    if timestamp is not None:
        from flask import current_app
        time = datetime.fromtimestamp(timestamp)
        return time.strftime(current_app.config.get(format_key, '%Y/%m/%d'))
    return ''


# SQLite record
class BrickRecord(object):
    select_query: str
    insert_query: str

    # Fields
    fields: BrickRecordFields

    def __init__(self, /):
        self.fields = BrickRecordFields()

    # Load from a record
    def ingest(self, record: Row | dict[str, Any], /) -> None:
        # Brutally ingest the record
        for key in record.keys():
            setattr(self.fields, key, record[key])

    # Insert into the database
    # If we do not commit immediately, we defer the execute() call
    def insert(
        self,
        /,
        *,
        commit=True,
        no_defer=False,
        override_query: str | None = None
    ) -> None:
        if override_query:
            query = override_query
        else:
            query = self.insert_query

        database = BrickSQL()
        database.execute(
            query,
            parameters=self.sql_parameters(),
            defer=not commit and not no_defer,
        )

        if commit:
            database.commit()

    # Shorthand to field items
    def items(self, /) -> ItemsView[str, Any]:
        return self.fields.__dict__.items()

    # Get from the database using the query
    def select(
        self,
        /,
        *,
        override_query: str | None = None,
        **context: Any
    ) -> bool:
        if override_query:
            query = override_query
        else:
            query = self.select_query

        record = BrickSQL().fetchone(
            query,
            parameters=self.sql_parameters(),
            **context
        )

        # Ingest the record
        if record is not None:
            self.ingest(record)

            return True

        else:
            return False

    # Generic SQL parameters from fields
    def sql_parameters(self, /) -> dict[str, Any]:
        parameters: dict[str, Any] = {}
        for name, value in self.items():
            parameters[name] = value

        return parameters
