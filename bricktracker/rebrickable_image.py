import logging
import os
import time
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from flask import current_app, url_for
import requests
import urllib3
from shutil import copyfileobj

from .exceptions import DownloadException
if TYPE_CHECKING:
    from .rebrickable_minifigure import RebrickableMinifigure
    from .rebrickable_part import RebrickablePart
    from .rebrickable_set import RebrickableSet

logger = logging.getLogger(__name__)

# Local patch: the Rebrickable CDN is unreliable from some networks
# (read timeouts, IncompleteRead, RemoteDisconnected). Without retries a
# single failed image aborts the import of an entire set.
DOWNLOAD_ATTEMPTS = 5
DOWNLOAD_TIMEOUT = 30
DOWNLOAD_BACKOFF = 2


# A set, part or minifigure image from Rebrickable
class RebrickableImage(object):
    set: 'RebrickableSet'
    minifigure: 'RebrickableMinifigure | None'
    part: 'RebrickablePart | None'

    extension: str | None

    def __init__(
        self,
        set: 'RebrickableSet',
        /,
        *,
        minifigure: 'RebrickableMinifigure | None' = None,
        part: 'RebrickablePart | None' = None,
    ):
        # Save all objects
        self.set = set
        self.minifigure = minifigure
        self.part = part

        # Currently everything is saved as 'jpg'
        self.extension = 'jpg'

        # Guess the extension
        # url = self.url()
        # if url is not None:
        #     _, extension = os.path.splitext(url)
        #     # TODO: Add allowed extensions
        #     if extension != '':
        #         self.extension = extension

    # Import the image from Rebrickable
    def download(self, /) -> None:
        path = self.path()

        # Avoid doing anything if the file exists
        if os.path.exists(path):
            return

        # Get the URL (this handles nil images via url() method)
        url = self.url()
        if not url:
            return

        # Grab the image, retrying on transient network errors.
        # Written to a temporary file first so an interrupted download does
        # not leave a truncated file that the os.path.exists() check above
        # would later mistake for a valid cache entry.
        temporary_path = '{path}.part'.format(path=path)

        for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
            try:
                response = requests.get(
                    url,
                    stream=True,
                    timeout=DOWNLOAD_TIMEOUT,
                )

                if not response.ok:
                    raise DownloadException(
                        'could not get image {id} at {url}'.format(
                            id=self.id(),
                            url=url,
                        )
                    )

                with open(temporary_path, 'wb') as f:
                    copyfileobj(response.raw, f)

                os.replace(temporary_path, path)

                return

            except (
                requests.RequestException,
                urllib3.exceptions.HTTPError,
                DownloadException,
                OSError,
            ) as e:
                try:
                    os.remove(temporary_path)
                except OSError:
                    pass

                if attempt < DOWNLOAD_ATTEMPTS:
                    time.sleep(DOWNLOAD_BACKOFF ** (attempt - 1))
                    continue

                # The image is only a local cache: the application already
                # falls back to a placeholder when a file is absent, and a
                # later set refresh will try again. Losing one image must not
                # abort the import of a whole set.
                logger.warning(
                    'Giving up on image {id} at {url} after {n} attempts: {e}'.format(  # noqa: E501
                        id=self.id(),
                        url=url,
                        n=DOWNLOAD_ATTEMPTS,
                        e=e,
                    )
                )

    # Return the folder depending on the objects provided
    def folder(self, /) -> str:
        if self.part is not None:
            return current_app.config['PARTS_FOLDER']

        if self.minifigure is not None:
            return current_app.config['MINIFIGURES_FOLDER']

        return current_app.config['SETS_FOLDER']

    # Return the id depending on the objects provided
    def id(self, /) -> str:
        if self.part is not None:
            if self.part.fields.image_id is None:
                return RebrickableImage.nil_name()
            else:
                return self.part.fields.image_id

        if self.minifigure is not None:
            if not self.minifigure.fields.image:
                return RebrickableImage.nil_minifigure_name()
            else:
                return self.minifigure.fields.figure

        return self.set.fields.set

    # Return the path depending on the objects provided
    def path(self, /) -> str:
        folder = self.folder()
        # If folder is an absolute path (starts with /), use it directly
        # Otherwise, make it relative to app root (current_app.root_path)
        if folder.startswith('/'):
            base_path = folder
        else:
            base_path = os.path.join(current_app.root_path, folder)

        return os.path.join(
            base_path,
            '{id}.{ext}'.format(id=self.id(), ext=self.extension),
        )

    # Return the url depending on the objects provided
    def url(self, /) -> str:
        if self.part is not None:
            if not self.part.fields.image:
                return current_app.config['REBRICKABLE_IMAGE_NIL']
            else:
                return self.part.fields.image

        if self.minifigure is not None:
            if not self.minifigure.fields.image:
                return current_app.config['REBRICKABLE_IMAGE_NIL_MINIFIGURE']
            else:
                return self.minifigure.fields.image

        # Handle set images - use nil placeholder if image is null
        if self.set.fields.image is None:
            return current_app.config['REBRICKABLE_IMAGE_NIL']
        else:
            return self.set.fields.image

    # Return the name of the nil image file
    @staticmethod
    def nil_name() -> str:
        filename, _ = os.path.splitext(
            os.path.basename(
                urlparse(current_app.config['REBRICKABLE_IMAGE_NIL']).path
            )
        )

        return filename

    # Return the name of the nil minifigure image file
    @staticmethod
    def nil_minifigure_name() -> str:
        filename, _ = os.path.splitext(
            os.path.basename(
                urlparse(current_app.config['REBRICKABLE_IMAGE_NIL_MINIFIGURE']).path  # noqa: E501
            )
        )

        return filename

    # Return the static URL for an image given a name and folder
    @staticmethod
    def static_url(name: str, folder_name: str) -> str:
        folder: str = current_app.config[folder_name]

        # /!\ Everything is saved as .jpg, even if it came from a .png
        # not changing this behaviour.

        # Grab the extension
        # _, extension = os.path.splitext(self.part_img_url)
        extension = '.jpg'

        # Determine which route to use based on folder path
        # If folder contains 'data' (new structure), use data route
        # Otherwise use static route (legacy - relative paths like 'parts', 'sets')
        if 'data' in folder:
            # Extract the folder type from the folder_name config key
            # E.g., 'PARTS_FOLDER' -> 'parts', 'SETS_FOLDER' -> 'sets'
            folder_type = folder_name.replace('_FOLDER', '').lower()
            filename = '{name}{ext}'.format(name=name, ext=extension)
            return url_for('data.serve_data_file', folder=folder_type, filename=filename)
        else:
            # Legacy: folder is relative to static/ (e.g., 'parts' or 'static/parts')
            # Strip 'static/' prefix if present to avoid double /static/ in URL
            folder_clean = folder.removeprefix('static/')
            path = os.path.join(folder_clean, '{name}{ext}'.format(
                name=name,
                ext=extension,
            ))
            return url_for('static', filename=path)
