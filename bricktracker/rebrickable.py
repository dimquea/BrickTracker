import json
import logging
import time
from typing import Any, Callable, Generic, Type, TypeVar, TYPE_CHECKING
from urllib.error import HTTPError

from flask import current_app
from rebrick import lego

from .exceptions import NotFoundException, ErrorException
if TYPE_CHECKING:
    from .minifigure import BrickMinifigure
    from .part import BrickPart
    from .rebrickable_set import RebrickableSet
    from .set import BrickSet
    from .socket import BrickSocket
    from .wish import BrickWish

T = TypeVar('T', 'RebrickableSet', 'BrickPart', 'BrickMinifigure', 'BrickWish')

logger = logging.getLogger(__name__)

# Local patch: retry transport errors talking to the Rebrickable API.
API_ATTEMPTS = 5
API_BACKOFF = 2


# An helper around the rebrick library, autoconverting
class Rebrickable(Generic[T]):
    method: Callable
    method_name: str
    number: str
    model: Type[T]

    brickset: 'BrickSet | None'
    instance: T | None
    kind: str
    minifigure: 'BrickMinifigure | None'
    socket: 'BrickSocket | None'

    def __init__(
        self,
        method: str,
        number: str,
        model: Type[T],
        /,
        *,
        brickset: 'BrickSet | None' = None,
        instance: T | None = None,
        minifigure: 'BrickMinifigure | None' = None,
        socket: 'BrickSocket | None' = None,
    ):
        if not hasattr(lego, method):
            raise ErrorException('{method} is not a valid method for the rebrick.lego module'.format(  # noqa: E501
                method=method,
            ))

        self.method = getattr(lego, method)
        self.method_name = method
        self.number = number
        self.model = model

        self.brickset = brickset
        self.instance = instance
        self.minifigure = minifigure
        self.socket = socket

        if self.minifigure is not None:
            self.kind = 'Minifigure'
        else:
            self.kind = 'Set'

    # Get one element from the Rebrickable API
    def get(self, /) -> T:
        model_parameters = self.model_parameters()

        if self.instance is None:
            self.instance = self.model(**model_parameters)

        self.instance.ingest(self.model.from_rebrickable(
            self.load(),
            brickset=self.brickset,
        ))

        return self.instance

    # Get paginated elements from the Rebrickable API
    def list(self, /) -> list[T]:
        model_parameters = self.model_parameters()

        results: list[T] = []

        # Bootstrap a first set of parameters
        parameters: dict[str, Any] | None = {
            'page_size': current_app.config['REBRICKABLE_PAGE_SIZE'],
        }

        # Read all pages
        while parameters is not None:
            response = self.load(parameters=parameters)

            # Grab the results
            if 'results' not in response:
                raise ErrorException('Missing "results" field from {method} for {number}'.format(  # noqa: E501
                    method=self.method_name,
                    number=self.number,
                ))

            # Update the total
            if self.socket is not None:
                self.socket.total_progress(len(response['results']), add=True)

            # Convert to object
            for result in response['results']:
                results.append(
                    self.model(
                        **model_parameters,
                        record=self.model.from_rebrickable(result),
                    )
                )

            # Check for a next page
            if 'next' in response and response['next'] is not None:
                parameters['page'] = response['next']
            else:
                parameters = None

        return results

    # Load from the API
    def load(self, /, *, parameters: dict[str, Any] = {}) -> dict[str, Any]:
        # Inject the API key
        parameters['api_key'] = current_app.config['REBRICKABLE_API_KEY']

        # Local patch: the Rebrickable API is unreliable from some networks
        # (IncompleteRead, connection resets mid-response). A single blip
        # would otherwise abort the import of an entire set, so transport
        # errors are retried with a backoff. HTTP status errors are not
        # retried: a 404 is an answer, not a failure to get one.
        for attempt in range(1, API_ATTEMPTS + 1):
            try:
                return json.loads(
                    self.method(
                        self.number,
                        **parameters,
                    ).read()
                )

            # HTTP errors
            except HTTPError as e:
                # Not found
                if e.code == 404:
                    raise NotFoundException('{kind} {number} was not found on Rebrickable'.format(  # noqa: E501
                        kind=self.kind,
                        number=self.number,
                    ))
                else:
                    # Re-raise as ErrorException
                    raise ErrorException(e)

            # Other errors
            except Exception as e:
                if attempt < API_ATTEMPTS:
                    logger.warning(
                        'Rebrickable {method} for {number} failed (attempt {a}/{n}): {e}'.format(  # noqa: E501
                            method=self.method_name,
                            number=self.number,
                            a=attempt,
                            n=API_ATTEMPTS,
                            e=e,
                        )
                    )
                    time.sleep(API_BACKOFF ** (attempt - 1))
                    continue

                # Re-raise as ErrorException
                raise ErrorException(e)

        # Unreachable: the loop either returns or raises
        raise ErrorException('exhausted retries for {number}'.format(
            number=self.number,
        ))

    # Get the model parameters
    def model_parameters(self, /) -> dict[str, Any]:
        parameters: dict[str, Any] = {}

        # Overload with objects
        if self.brickset is not None:
            parameters['brickset'] = self.brickset

        if self.minifigure is not None:
            parameters['minifigure'] = self.minifigure

        return parameters
