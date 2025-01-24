from datetime import datetime, timezone
import logging
import os
from typing import TYPE_CHECKING

from flask import current_app, g, url_for, flash
import humanize
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from io import BytesIO
import requests
from bs4 import BeautifulSoup

from .exceptions import ErrorException
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
       
     # Compute the url for the rebrickable instructions page
    def url_for_instructions(self, /) -> str:       
        try:
            return current_app.config['REBRICKABLE_LINK_INSTRUCTIONS_PATTERN'].format(  # noqa: E501
                number=self.filename,
            )
        except Exception:
            pass

        return ''
    
    def find_instructions(self, set: str, /) -> None:
            
        headers = {
            'User-Agent': current_app.config['REBRICKABLE_USER_AGENT']
        }
        
        response = requests.get(BrickInstructions.url_for_instructions(self), headers=headers)
        if response.status_code != 200:
            raise ErrorException('Failed to load page. Status code: {response.status_code}')
        
        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Collect all <img> tags with "LEGO Building Instructions" in the alt attribute
        found_tags = []
        for a_tag in soup.find_all('a', href=True):
            img_tag = a_tag.find('img', alt=True)
            if img_tag and "LEGO Building Instructions" in img_tag['alt']:
                found_tags.append((img_tag['alt'].replace('LEGO Building Instructions for ', ''), a_tag['href']))  # Save alt and href
        
        return found_tags
    
    def get_list(self, request_form, /) -> list:
        selected_instructions = []
        # Get the list of instructions
        for key in request_form:
            if key.startswith('instruction-') and request_form.get(key) == 'on':  # Checkbox is checked
                index = key.split('-')[-1]
                alt_text = request_form.get(f'instruction-alt-text-{index}')
                href_text = request_form.get(f'instruction-href-text-{index}').replace('/instructions/', '')  # Remove the /instructions/ part
                selected_instructions.append((href_text,alt_text))

        return selected_instructions
        
    def download(self, href: str, /) -> None:     
        target = self.path(filename=secure_filename(self.filename))

        if os.path.isfile(target):
            raise ErrorException('Cannot download {target} as it already exists'.format(  # noqa: E501
                target=self.filename
            ))

        url = current_app.config['REBRICKABLE_LINK_INSTRUCTIONS_PATTERN'].format(number=href)

        response = requests.get(url)
        if response.status_code == 200:
            # Save the content to the target path
            FileStorage(stream=BytesIO(response.content)).save(target)
        else:
            raise ErrorException(f"Failed to download {self.filename}. Status code: {response.status_code}")

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
