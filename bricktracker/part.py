import logging
from sqlite3 import Row
from typing import Any, Self, TYPE_CHECKING
import traceback

from flask import url_for

from .exceptions import ErrorException, NotFoundException
from .rebrickable_part import RebrickablePart
from .sql import BrickSQL
if TYPE_CHECKING:
    from .minifigure import BrickMinifigure
    from .set import BrickSet
    from .socket import BrickSocket

logger = logging.getLogger(__name__)


# Lego set or minifig part
class BrickPart(RebrickablePart):
    identifier: str
    kind: str

    # Queries
    insert_query: str = 'part/insert'
    generic_query: str = 'part/select/generic'
    select_query: str = 'part/select/specific'

    def __init__(
        self,
        /,
        *,
        brickset: 'BrickSet | None' = None,
        minifigure: 'BrickMinifigure | None' = None,
        record: Row | dict[str, Any] | None = None
    ):
        super().__init__(
            brickset=brickset,
            minifigure=minifigure,
            record=record
        )

        if self.minifigure is not None:
            self.identifier = self.minifigure.fields.figure
            self.kind = 'Minifigure'
        elif self.brickset is not None:
            self.identifier = self.brickset.fields.set
            self.kind = 'Set'

    # Import a part into the database
    def download(self, socket: 'BrickSocket', refresh: bool = False) -> bool:
        if self.brickset is None:
            raise ErrorException('Importing a part from Rebrickable outside of a set is not supported')  # noqa: E501

        try:
            # Insert into the database
            socket.auto_progress(
                message='{kind} {identifier}: inserting part {part} into database'.format(  # noqa: E501
                    kind=self.kind,
                    identifier=self.identifier,
                    part=self.fields.part
                )
            )

            if not refresh:
                # Insert into database
                self.insert(commit=False)

            # Insert the rebrickable set into database
            self.insert_rebrickable()

        except Exception as e:
            socket.fail(
                message='Error while importing part {part} from {kind} {identifier}: {error}'.format(  # noqa: E501
                    part=self.fields.part,
                    kind=self.kind,
                    identifier=self.identifier,
                    error=e,
                )
            )

            logger.debug(traceback.format_exc())

            return False

        return True

    # A identifier for HTML component
    def html_id(self, prefix: str | None = None, /) -> str:
        components: list[str] = ['part']

        if prefix is not None:
            components.append(prefix)

        if self.fields.figure is not None:
            components.append(self.fields.figure)

        components.append(self.fields.part)
        components.append(str(self.fields.color))
        components.append(str(self.fields.spare))

        return '-'.join(components)

    # Select a generic part
    def select_generic(
        self,
        part: str,
        color: int,
        /,
    ) -> Self:
        # Save the parameters to the fields
        self.fields.part = part
        self.fields.color = color

        if not self.select(override_query=self.generic_query):
            raise NotFoundException(
                'Part with number {number}, color ID {color} was not found in the database'.format(  # noqa: E501
                    number=self.fields.part,
                    color=self.fields.color,
                ),
            )

        return self

    # Select a specific part (with a set and an id, and option. a minifigure)
    def select_specific(
        self,
        brickset: 'BrickSet',
        part: str,
        color: int,
        spare: int,
        /,
        *,
        minifigure: 'BrickMinifigure | None' = None,
    ) -> Self:
        # Save the parameters to the fields
        self.brickset = brickset
        self.minifigure = minifigure
        self.fields.part = part
        self.fields.color = color
        self.fields.spare = spare

        if not self.select():
            if self.minifigure is not None:
                figure = self.minifigure.fields.figure
            else:
                figure = None

            raise NotFoundException(
                'Part {part} with color {color} (spare: {spare}) from set {set} ({id}) (minifigure: {figure}) was not found in the database'.format(  # noqa: E501
                    part=self.fields.part,
                    color=self.fields.color,
                    spare=self.fields.spare,
                    id=self.fields.id,
                    set=self.brickset.fields.set,
                    figure=figure,
                ),
            )

        return self

    # Update checked state for part walkthrough
    def update_checked(self, json: Any | None, /) -> bool:
        # Handle both direct 'checked' key and changer.js 'value' key format
        if json:
            checked = json.get('checked', json.get('value', False))
        else:
            checked = False

        checked = bool(checked)

        # Update the field
        self.fields.checked = checked

        BrickSQL().execute_and_commit(
            'part/update/checked',
            parameters=self.sql_parameters()
        )

        return checked

    # Compute the url for updating checked state
    def url_for_checked(self, /) -> str:
        # Check if this is an individual minifigure (has minifigure with id field, no brickset)
        if self.minifigure is not None and hasattr(self.minifigure.fields, 'id') and self.brickset is None:
            # Individual minifigure part
            return url_for(
                'individual_minifigure.checked_part',
                id=self.minifigure.fields.id,
                part=self.fields.part,
                color=self.fields.color,
                spare=self.fields.spare,
            )

        # Set-based part (with or without minifigure)
        if self.minifigure is not None:
            figure = self.minifigure.fields.figure
        else:
            figure = None

        return url_for(
            'set.checked_part',
            id=self.fields.id,
            figure=figure,
            part=self.fields.part,
            color=self.fields.color,
            spare=self.fields.spare,
        )

    # Update a problematic part
    def update_problem(self, problem: str, json: Any | None, /) -> int:
        amount: str | int = json.get('value', '')  # type: ignore

        # We need a positive integer
        try:
            if amount == '':
                amount = 0

            amount = int(amount)

            if amount < 0:
                amount = 0
        except Exception:
            raise ErrorException('"{amount}" is not a valid integer'.format(
                amount=amount
            ))

        if amount < 0:
            raise ErrorException('Cannot set a negative amount')

        setattr(self.fields, problem, amount)

        BrickSQL().execute_and_commit(
            'part/update/{problem}'.format(problem=problem),
            parameters=self.sql_parameters()
        )

        return amount

    # Compute the url for problematic part
    def url_for_problem(self, problem: str, /) -> str:
        # Check if this is an individual minifigure (has minifigure with id field, no brickset)
        if self.minifigure is not None and hasattr(self.minifigure.fields, 'id') and self.brickset is None:
            # Individual minifigure part
            return url_for(
                'individual_minifigure.problem_part',
                id=self.minifigure.fields.id,
                part=self.fields.part,
                color=self.fields.color,
                spare=self.fields.spare,
                problem=problem,
            )

        # Set-based part (with or without minifigure)
        if self.minifigure is not None:
            figure = self.minifigure.fields.figure
        else:
            figure = None

        return url_for(
            'set.problem_part',
            id=self.fields.id,
            figure=figure,
            part=self.fields.part,
            color=self.fields.color,
            spare=self.fields.spare,
            problem=problem,
        )

    # Select a specific part from an individual minifigure
    def select_specific_individual_minifigure(
        self,
        minifigure: 'BrickMinifigure',
        part: str,
        color: int,
        spare: int,
        /,
    ) -> Self:
        # Save the parameters to the fields
        self.minifigure = minifigure
        self.fields.id = minifigure.fields.id
        self.fields.part = part
        self.fields.color = color
        self.fields.spare = spare

        if not self.select(override_query='individual_minifigure/part/select/specific'):
            raise NotFoundException(
                'Part {part} with color {color} (spare: {spare}) from individual minifigure {figure} ({id}) was not found in the database'.format(
                    part=self.fields.part,
                    color=self.fields.color,
                    spare=self.fields.spare,
                    figure=self.minifigure.fields.figure,
                    id=self.minifigure.fields.id,
                ),
            )

        return self

    # Update a problematic part for individual minifigure
    def update_problem_individual_minifigure(self, problem: str, json: Any | None, /) -> int:
        amount: str | int = json.get('value', '')  # type: ignore

        # We need a positive integer
        try:
            if amount == '':
                amount = 0

            amount = int(amount)

            if amount < 0:
                amount = 0
        except Exception:
            raise ErrorException('"{amount}" is not a valid integer'.format(
                amount=amount
            ))

        if amount < 0:
            raise ErrorException('Cannot set a negative amount')

        setattr(self.fields, problem, amount)

        BrickSQL().execute_and_commit(
            'individual_minifigure/part/update/{problem}'.format(problem=problem),
            parameters=self.sql_parameters()
        )

        return amount

    # Update checked state for individual minifigure part
    def update_checked_individual_minifigure(self, json: Any | None, /) -> bool:
        # Handle both direct 'checked' key and changer.js 'value' key format
        if json:
            checked = json.get('checked', json.get('value', False))
        else:
            checked = False

        checked = bool(checked)

        # Update the field
        self.fields.checked = checked

        BrickSQL().execute_and_commit(
            'individual_minifigure/part/update/checked',
            parameters=self.sql_parameters()
        )

        return checked
