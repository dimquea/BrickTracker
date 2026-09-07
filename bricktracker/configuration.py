import os
from typing import Any, Type


# Configuration item
class BrickConfiguration(object):
    name: str
    cast: Type | None
    default: Any
    env_name: str
    extra_name: str | None
    mandatory: bool
    static_path: bool
    value: Any

    def __init__(
        self,
        /,
        *,
        n: str,
        e: str | None = None,
        d: Any = None,
        c: Type | None = None,
        m: bool = False,
        s: bool = False,
    ):
        # We prefix all default variable name with 'BK_' for the
        # environment name to avoid interfering
        self.name = n
        self.env_name = 'BK_{name}'.format(name=n)
        self.extra_name = e
        self.default = d
        self.cast = c
        self.mandatory = m
        self.static_path = s

        # Default for our booleans is False
        if self.cast == bool:
            self.default = False

        # Try default environment name
        value = os.getenv(self.env_name)
        if value is None:
            # Try the extra name
            if self.extra_name is not None:
                value = os.getenv(self.extra_name)

            # Set the default
            if value is None:
                value = self.default

        # Special treatment
        if value is not None:
            # Comma seperated list
            if self.cast == list and isinstance(value, str):
                value = [item.strip() for item in value.split(',')]
                self.cast = None

            # Boolean string
            if self.cast == bool and isinstance(value, str):
                value = value.lower() in ('true', 'yes', '1')

            # Static path fixup (legacy - only for paths with s: True flag)
            if self.static_path and isinstance(value, str):
                value = os.path.normpath(value)

                # Remove any leading slash or dots
                value = value.lstrip('/.')

                # Remove static prefix
                value = value.removeprefix('static/')

            # Normalize regular paths (not marked as static)
            elif not self.static_path and isinstance(value, str) and ('FOLDER' in self.name or 'PATH' in self.name):
                value = os.path.normpath(value)

        # Type casting
        if self.cast is not None:
            self.value = self.cast(value)
        else:
            self.value = value

    # Tells whether the value is changed from its default
    def is_changed(self, /) -> bool:
        return self.value != self.default

    # Tells whether the value is secret
    def is_secret(self, /) -> bool:
        return self.name in [
            'AUTHENTICATION_PASSWORD',
            'AUTHENTICATION_KEY'
        ]
