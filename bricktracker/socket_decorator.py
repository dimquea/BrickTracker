from functools import wraps
from threading import Thread
from typing import Callable, ParamSpec, TYPE_CHECKING, Union

from flask import copy_current_request_context

from .login import LoginManager
if TYPE_CHECKING:
    from .socket import BrickSocket

# What a threaded function can return (None or Thread)
SocketReturn = Union[None, Thread]

# Threaded signature (*arg, **kwargs -> (None or Thread)
P = ParamSpec('P')
SocketCallable = Callable[P, SocketReturn]


# Fail if not authenticated
def authenticated_socket(
    self: 'BrickSocket',
    /,
    *,
    threaded: bool = True,
) -> Callable[[SocketCallable], SocketCallable]:
    def outer(function: SocketCallable, /) -> SocketCallable:
        @wraps(function)
        def wrapper(*args, **kwargs) -> SocketReturn:
            # Needs to be authenticated
            if LoginManager.is_not_authenticated():
                self.fail(message='You need to be authenticated')
                return

            # Apply threading
            if threaded:
                return threaded_socket(self)(function)(*args, **kwargs)
            else:
                return function(*args, **kwargs)

        return wrapper
    return outer


# Fail if the BrickLink catalog is not available (authenticated, catalog)
# Automatically makes it threaded
#
# Пришёл на смену проверке ключа Rebrickable: ключа больше нет, а нужен
# скачанный дамп каталога.
def catalog_socket(
    self: 'BrickSocket',
    /,
    *,
    threaded: bool = True,
) -> Callable[[SocketCallable], SocketCallable]:
    def outer(function: SocketCallable, /) -> SocketCallable:
        @wraps(function)
        # Automatically authenticated
        @authenticated_socket(self, threaded=False)
        def wrapper(*args, **kwargs) -> SocketReturn:
            from .bricklink_catalog import BrickLinkCatalog

            if not BrickLinkCatalog().exists():
                self.fail(message='The BrickLink catalog has not been downloaded yet. Update it from the admin page.')  # noqa: E501
                return

            # Apply threading
            if threaded:
                return threaded_socket(self)(function)(*args, **kwargs)
            else:
                return function(*args, **kwargs)

        return wrapper
    return outer


# Start the function in a thread if the socket is threaded
def threaded_socket(
    self: 'BrickSocket',
    /
) -> Callable[[SocketCallable], SocketCallable]:
    def outer(function: SocketCallable, /) -> SocketCallable:
        @wraps(function)
        def wrapper(*args, **kwargs) -> SocketReturn:
            # Start it in a thread if requested
            if self.threaded:
                @copy_current_request_context
                def do_function() -> None:
                    function(*args, **kwargs)

                return self.socket.start_background_task(do_function)
            else:
                return function(*args, **kwargs)
        return wrapper
    return outer
