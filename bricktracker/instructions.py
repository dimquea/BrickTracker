from datetime import datetime, timezone
import logging
import os
from urllib.parse import urljoin
from shutil import copyfileobj
import traceback
from typing import Tuple, TYPE_CHECKING

from bs4 import BeautifulSoup
from flask import current_app, g, url_for
import humanize
import requests
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
import re

from .exceptions import ErrorException, DownloadException
if TYPE_CHECKING:
    from .rebrickable_set import RebrickableSet
    from .socket import BrickSocket

logger = logging.getLogger(__name__)


class BrickInstructions(object):
    socket: 'BrickSocket'

    allowed: bool
    rebrickable: 'RebrickableSet | None'
    extension: str
    filename: str
    mtime: datetime
    set: 'str | None'
    name: str
    size: int

    def __init__(
        self,
        file: os.DirEntry | str,
        /,
        *,
        socket: 'BrickSocket | None' = None,
    ):
        # Save the socket
        if socket is not None:
            self.socket = socket

        if isinstance(file, str):
            self.filename = file

            if self.filename == '':
                raise ErrorException('An instruction filename cannot be empty')
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

            if len(splits) >= 2 and splits[0]:
                try:
                    # The set number can be alphanumeric (e.g. Pick-a-Brick
                    # builds like "EG00029-1"); only the version suffix has
                    # to be an integer
                    int(splits[1])

                    self.set = '-'.join(splits[:2])
                except Exception:
                    pass

    # Delete an instruction file
    def delete(self, /) -> None:
        os.remove(self.path())

    # Download an instruction file
    def download(self, path: str, /) -> None:
        """
        Streams the PDF in chunks and uses self.socket.update_total
        + self.socket.progress_count to drive a determinate bar.
        """
        try:
            target = self.path(filename=secure_filename(self.filename))

            # Skip if we already have it
            if os.path.isfile(target):
                pdf_url = self.url()
                return self.socket.complete(
                    message=f'File {self.filename} already exists, skipped - <a href="{pdf_url}" target="_blank" class="btn btn-sm btn-primary ms-2"><i class="ri-external-link-line"></i> Open PDF</a>'
                )

            # Use plain requests instead of cloudscraper
            session = requests.Session()
            session.headers.update({
                'User-Agent': current_app.config['USER_AGENT'],
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Cache-Control': 'max-age=0'
            })

            resp = session.get(path, stream=True, allow_redirects=True)
            if not resp.ok:
                raise DownloadException(f"Failed to download: HTTP {resp.status_code}")

            # Tell the socket how many bytes in total
            total = int(resp.headers.get("Content-Length", 0))
            self.socket.update_total(total)

            # Reset the counter and kick off at 0%
            self.socket.progress_count = 0
            self.socket.progress(message=f"Starting download {self.filename}")

            # Write out in 8 KiB chunks and update the counter
            with open(target, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if not chunk:
                        continue
                    f.write(chunk)

                    # Bump the internal counter and emit
                    self.socket.progress_count += len(chunk)
                    self.socket.progress(
                        message=(
                            f"Downloading {self.filename} "
                            f"({humanize.naturalsize(self.socket.progress_count)}/"
                            f"{humanize.naturalsize(self.socket.progress_total)})"
                        )
                    )

            # Done!
            logger.info(f"Downloaded {self.filename}")
            pdf_url = self.url()
            self.socket.complete(
                message=f'File {self.filename} downloaded ({self.human_size()}) - <a href="{pdf_url}" target="_blank" class="btn btn-sm btn-primary ms-2"><i class="ri-external-link-line"></i> Open PDF</a>'
            )

        except Exception as e:
            logger.debug(traceback.format_exc())
            self.socket.fail(
                message=f"Error downloading {self.filename}: {e}"
            )

    # Display the size in a human format
    def human_size(self) -> str:
        try:
            size = self.size
        except AttributeError:
            size = os.path.getsize(self.path())
        return humanize.naturalsize(size)

    # Display the time in a human format
    def human_time(self) -> str:
        return self.mtime.astimezone(g.timezone).strftime(
            current_app.config['FILE_DATETIME_FORMAT']
        )

    # Compute the path of an instruction file
    def path(self, /, *, filename=None) -> str:
        if filename is None:
            filename = self.filename

        folder = current_app.config['INSTRUCTIONS_FOLDER']

        # If folder is absolute, use it directly
        # Otherwise, make it relative to app root (not static folder)
        if os.path.isabs(folder):
            base_path = folder
        else:
            base_path = os.path.join(current_app.root_path, folder)

        return os.path.join(base_path, filename)

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

        # Determine which route to use based on folder path
        # If folder contains 'data' (new structure), use data route
        # Otherwise use static route (legacy)
        if 'data' in folder:
            return url_for('data.serve_data_file', folder='instructions', filename=self.filename)
        else:
            # Legacy: folder is relative to static/
            folder_clean = folder.removeprefix('static/')
            path = os.path.join(folder_clean, self.filename)
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

    # Find the instructions for a set
    @staticmethod
    def find_instructions(set: str, /) -> list[Tuple[str, str]]:
        """
        Scrape LEGO's official building-instructions page and return a list
        of (filename_slug, download_url). Duplicate slugs get _1, _2, …
        """
        # LEGO's page wants the bare set number, no "-1" version suffix
        number, _, _version = set.partition('-')

        page_url = f"https://www.lego.com/en-us/service/building-instructions/{number}"  # noqa: E501
        logger.debug(f"[find_instructions] fetching HTML from {page_url!r}")

        # Use plain requests instead of cloudscraper
        session = requests.Session()
        session.headers.update({
            'User-Agent': current_app.config['USER_AGENT'],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })

        resp = session.get(page_url)
        if not resp.ok:
            raise ErrorException(f'Failed to load instructions page for {set}. HTTP {resp.status_code}')

        soup = BeautifulSoup(resp.content, 'html.parser')

        # Each booklet is a "bi-card" div. Attribute order on this page is
        # not stable between requests, so every lookup has to stay scoped
        # inside its own card rather than collecting all h3s/links
        # page-wide and pairing them up by position, that can silently
        # mismatch a label with the wrong link.
        raw: list[tuple[str, str]] = []
        for card in soup.find_all('div', attrs={'data-test': 'bi-card'}):
            label = card.find('h3')
            link = card.find('a', attrs={'data-test': 'bi-card-link'})

            if label is None or link is None or not link.get('href'):
                continue

            # Prefix with the set number: filenames are how a downloaded
            # instruction later gets matched back to its set (see
            # BrickInstructions.__init__), and LEGO's own card labels never
            # mention the set number, only the product name and booklet.
            card_slug = re.sub(r'[^A-Za-z0-9]+', '-', label.get_text(strip=True)).strip('-')  # noqa: E501
            slug = f'{set}-{card_slug}'
            download_url = urljoin('https://www.lego.com', link['href'])

            logger.debug(f"[find_instructions] Found download link: {download_url}")  # noqa: E501
            raw.append((slug, download_url))

        if not raw:
            raise ErrorException(f'No download links found on instructions page for {set}')

        # Disambiguate duplicate slugs by appending _1, _2, …
        from collections import Counter, defaultdict
        counts = Counter(name for name, _ in raw)
        seen: dict[str, int] = defaultdict(int)
        unique: list[tuple[str, str]] = []
        for name, url in raw:
            idx = seen[name]
            if counts[name] > 1 and idx > 0:
                final_name = f"{name}_{idx}"
            else:
                final_name = name
            seen[name] += 1
            unique.append((final_name, url))

        return unique
