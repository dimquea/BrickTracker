from datetime import datetime, timezone
import logging
import os
from shutil import copyfileobj
from typing import Tuple, TYPE_CHECKING

from bs4 import BeautifulSoup
from flask import current_app, g, url_for
import humanize
import requests
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from .exceptions import ErrorException, DownloadException
from .parser import parse_set
if TYPE_CHECKING:
    from .rebrickable_set import RebrickableSet

logger = logging.getLogger(__name__)


class BrickInstructions(object):
    allowed: bool
    rebrickable: 'RebrickableSet | None'
    extension: str
    filename: str
    mtime: datetime
    set: 'str | None'
    name: str
    size: int

    def __init__(self, file: os.DirEntry | str, /):
        if isinstance(file, str):
            self.filename = file
        else:
            self.filename = file.name

            # Store the file stats
            stat = file.stat()
            self.size = stat.st_size
            self.mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)

        # Store the name and extension, check if extension is allowed
        self.name, self.extension = os.path.splitext(self.filename)
        self.extension = self.extension.lower()
        self.allowed = self.extension in current_app.config['INSTRUCTIONS_ALLOWED_EXTENSIONS']  # noqa: E501

        # Placeholder
        self.rebrickable = None
        self.set = None

        # Extract the set number
        if self.allowed:
            # Normalize special chars to improve set detection
            normalized = self.name.replace('_', '-')
            normalized = normalized.replace(' ', '-')

            splits = normalized.split('-', 2)

            if len(splits) >= 2:
                try:
                    # Trying to make sense of each part as integers
                    int(splits[0])
                    int(splits[1])

                    self.set = '-'.join(splits[:2])
                except Exception:
                    pass

    # Delete an instruction file
    def delete(self, /) -> None:
        os.remove(self.path())

    # Download an instruction file
    def download(self, path: str, /) -> None:
        target = self.path(filename=secure_filename(self.filename))

        if os.path.isfile(target):
            raise ErrorException('Cannot download {target} as it already exists'.format(  # noqa: E501
                target=self.filename
            ))

        url = current_app.config['REBRICKABLE_LINK_INSTRUCTIONS_PATTERN'].format(  # noqa: E501
            path=path
        )

        response = requests.get(url, stream=True)
        if response.ok:
            with open(target, 'wb') as f:
                copyfileobj(response.raw, f)
        else:
            raise DownloadException('Failed to download {file}. Status code: {code}'.format(  # noqa: E501
                file=self.filename,
                code=response.status_code
            ))

        # Info
        logger.info('The instruction file {file} has been downloaded'.format(
            file=self.filename
        ))

    # Display the size in a human format
    def human_size(self) -> str:
        return humanize.naturalsize(self.size)

    # Display the time in a human format
    def human_time(self) -> str:
        return self.mtime.astimezone(g.timezone).strftime(
            current_app.config['FILE_DATETIME_FORMAT']
        )

    # Compute the path of an instruction file
    def path(self, /, *, filename=None) -> str:
        if filename is None:
            filename = self.filename

        return os.path.join(
            current_app.static_folder,  # type: ignore
            current_app.config['INSTRUCTIONS_FOLDER'],
            filename
        )

    # Rename an instructions file
    def rename(self, filename: str, /) -> None:
        # Add the extension
        filename = '{name}{ext}'.format(name=filename, ext=self.extension)

        if filename != self.filename:
            # Check if it already exists
            target = self.path(filename=filename)
            if os.path.isfile(target):
                raise ErrorException('Cannot rename {source} to {target} as it already exists'.format(  # noqa: E501
                    source=self.filename,
                    target=filename
                ))

            os.rename(self.path(), target)

    # Upload a new instructions file
    def upload(self, file: FileStorage, /) -> None:
        target = self.path(filename=secure_filename(self.filename))

        if os.path.isfile(target):
            raise ErrorException('Cannot upload {target} as it already exists'.format(  # noqa: E501
                target=self.filename
            ))

        file.save(target)

        # Info
        logger.info('The instruction file {file} has been imported'.format(
            file=self.filename
        ))

    # Compute the url for a set instructions file
    def url(self, /) -> str:
        if not self.allowed:
            return ''

        folder: str = current_app.config['INSTRUCTIONS_FOLDER']

        # Compute the path
        path = os.path.join(folder, self.filename)

        return url_for('static', filename=path)

    # Return the icon depending on the extension
    def icon(self, /) -> str:
        if self.extension == '.pdf':
            return 'file-pdf-2-line'
        elif self.extension in ['.doc', '.docx']:
            return 'file-word-line'
        elif self.extension in ['.png', '.jpg', '.jpeg']:
            return 'file-image-line'
        else:
            return 'file-line'

    # Download selected instructions for a set
    @staticmethod
    def download_instructions(form: dict[str, str], /) -> None:
        selected_instructions: list[Tuple[str, str]] = []

        # Get the list of instructions
        for key in form:
            if key.startswith('instruction-') and form.get(key) == 'on':
                _, _, index = key.partition('-')
                alt_text = form.get(f'instruction-alt-text-{index}', '')
                href_text = form.get(f'instruction-href-text-{index}', '').removeprefix('/instructions/')  # Remove the /instructions/ part  # noqa: E501
                selected_instructions.append((href_text, alt_text))

        # Raise if nothing selected
        if not len(selected_instructions):
            raise ErrorException('No instruction was selected to download')

        # Loop over selected instructions and download them
        for href, filename in selected_instructions:
            BrickInstructions(f"{filename}.pdf").download(href)

    # Find the instructions for a set
    @staticmethod
    def find_instructions(form: dict[str, str], /) -> list[Tuple[str, str]]:
        # Grab the set ID
        set: str = form.get('add-set', '')

        # Parse it
        set = parse_set(set)

        response = requests.get(
            current_app.config['REBRICKABLE_LINK_INSTRUCTIONS_PATTERN'].format(
                path=set,
            ),
            headers={
                'User-Agent': current_app.config['REBRICKABLE_USER_AGENT']
            }
        )

        if not response.ok:
            raise ErrorException('Failed to load the Rebrickable instructions page. Status code: {code}'.format(  # noqa: E501
                code=response.status_code
            ))

        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')

        # Collect all <img> tags with "LEGO Building Instructions" in the
        # alt attribute
        found_tags: list[Tuple[str, str]] = []
        for a_tag in soup.find_all('a', href=True):
            img_tag = a_tag.find('img', alt=True)
            if img_tag and "LEGO Building Instructions" in img_tag['alt']:
                found_tags.append(
                    (
                        img_tag['alt'].removeprefix('LEGO Building Instructions for '),  # noqa: E501
                        a_tag['href']
                    )
                )  # Save alt and href

        # Raise an error if nothing found
        if not len(found_tags):
            raise ErrorException('No instruction found for set {set}'.format(
                set=set
            ))

        return found_tags
