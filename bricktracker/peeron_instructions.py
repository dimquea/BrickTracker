import hashlib
import logging
import os
from pathlib import Path
import time
from typing import Any, NamedTuple, TYPE_CHECKING
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from flask import current_app, url_for
import requests

from .exceptions import ErrorException
if TYPE_CHECKING:
    from .socket import BrickSocket

logger = logging.getLogger(__name__)


def get_peeron_user_agent():
    """Get the User-Agent string for Peeron requests from config"""
    return current_app.config.get('USER_AGENT',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')


def get_peeron_download_delay():
    """Get the delay in milliseconds between Peeron page downloads from config"""
    return current_app.config.get('PEERON_DOWNLOAD_DELAY', 1000)


def get_min_image_size():
    """Get the minimum image size for valid Peeron instruction pages from config"""
    return current_app.config.get('PEERON_MIN_IMAGE_SIZE', 100)


def get_peeron_instruction_url(set_number: str, version_number: str):
    """Get the Peeron instruction page URL using the configured pattern"""
    pattern = current_app.config.get('PEERON_INSTRUCTION_PATTERN', 'http://peeron.com/scans/{set_number}-{version_number}')
    return pattern.format(set_number=set_number, version_number=version_number)


def get_peeron_thumbnail_url(set_number: str, version_number: str):
    """Get the Peeron thumbnail base URL using the configured pattern"""
    pattern = current_app.config.get('PEERON_THUMBNAIL_PATTERN', 'http://belay.peeron.com/thumbs/{set_number}-{version_number}/')
    return pattern.format(set_number=set_number, version_number=version_number)


def get_peeron_scan_url(set_number: str, version_number: str):
    """Get the Peeron scan base URL using the configured pattern"""
    pattern = current_app.config.get('PEERON_SCAN_PATTERN', 'http://belay.peeron.com/scans/{set_number}-{version_number}/')
    return pattern.format(set_number=set_number, version_number=version_number)


def create_peeron_scraper():
    """Create a requests session configured for Peeron"""
    session = requests.Session()
    session.headers.update({
        "User-Agent": get_peeron_user_agent()
    })
    return session


def get_peeron_cache_dir():
    """Get the base directory for Peeron caching"""
    static_dir = Path(current_app.static_folder)
    cache_dir = static_dir / 'images' / 'peeron_cache'
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_set_cache_dir(set_number: str, version_number: str) -> tuple[Path, Path]:
    """Get cache directories for a specific set"""
    base_cache_dir = get_peeron_cache_dir()
    set_cache_key = f"{set_number}-{version_number}"

    full_cache_dir = base_cache_dir / 'full' / set_cache_key
    thumb_cache_dir = base_cache_dir / 'thumbs' / set_cache_key

    full_cache_dir.mkdir(parents=True, exist_ok=True)
    thumb_cache_dir.mkdir(parents=True, exist_ok=True)

    return full_cache_dir, thumb_cache_dir


def cache_full_image_and_generate_thumbnail(image_url: str, page_number: str, set_number: str, version_number: str, session=None) -> tuple[str | None, str | None]:
    """
    Download and cache full-size image, then generate a thumbnail preview.
    Uses the full-size scan URLs from Peeron.
    Returns (cached_image_path, thumbnail_url) or (None, None) if caching fails.
    """
    try:
        full_cache_dir, thumb_cache_dir = get_set_cache_dir(set_number, version_number)

        full_filename = f"{page_number}.jpg"
        thumb_filename = f"{page_number}.jpg"
        full_cache_path = full_cache_dir / full_filename
        thumb_cache_path = thumb_cache_dir / thumb_filename

        # Return existing cached files if they exist
        if full_cache_path.exists() and thumb_cache_path.exists():
            set_cache_key = f"{set_number}-{version_number}"
            thumbnail_url = url_for('static', filename=f'images/peeron_cache/thumbs/{set_cache_key}/{thumb_filename}')
            return str(full_cache_path), thumbnail_url

        # Download the full-size image using provided session or create new one
        if session is None:
            session = create_peeron_scraper()
        response = session.get(image_url, timeout=30)

        if response.status_code == 200 and len(response.content) > 0:
            # Validate it's actually an image by checking minimum size
            min_size = get_min_image_size()
            if len(response.content) < min_size:
                logger.warning(f"Image too small, skipping cache: {image_url}")
                return None, None

            # Write full-size image to cache
            with open(full_cache_path, 'wb') as f:
                f.write(response.content)

            logger.debug(f"Cached full image: {image_url} -> {full_cache_path}")

            # Generate thumbnail from the cached full image
            try:
                from PIL import Image
                with Image.open(full_cache_path) as img:
                    # Create thumbnail (max 150px on longest side to match template)
                    img.thumbnail((150, 150), Image.Resampling.LANCZOS)
                    img.save(thumb_cache_path, 'JPEG', quality=85)

                logger.debug(f"Generated thumbnail: {full_cache_path} -> {thumb_cache_path}")

                set_cache_key = f"{set_number}-{version_number}"
                thumbnail_url = url_for('static', filename=f'images/peeron_cache/thumbs/{set_cache_key}/{thumb_filename}')
                return str(full_cache_path), thumbnail_url

            except Exception as thumb_error:
                logger.error(f"Failed to generate thumbnail for {page_number}: {thumb_error}")
                # Clean up the full image if thumbnail generation failed
                if full_cache_path.exists():
                    full_cache_path.unlink()
                return None, None
        else:
            logger.warning(f"Failed to download full image: {image_url}")
            return None, None

    except Exception as e:
        logger.error(f"Error caching full image {image_url}: {e}")
        return None, None


def clear_set_cache(set_number: str, version_number: str) -> int:
    """
    Clear all cached files for a specific set after PDF generation.
    Returns the number of files deleted.
    """
    try:
        full_cache_dir, thumb_cache_dir = get_set_cache_dir(set_number, version_number)
        deleted_count = 0

        # Delete full images
        if full_cache_dir.exists():
            for cache_file in full_cache_dir.glob('*.jpg'):
                try:
                    cache_file.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted cached full image: {cache_file}")
                except OSError as e:
                    logger.warning(f"Failed to delete cache file {cache_file}: {e}")

            # Remove directory if empty
            try:
                full_cache_dir.rmdir()
            except OSError:
                pass  # Directory not empty or other error

        # Delete thumbnails
        if thumb_cache_dir.exists():
            for cache_file in thumb_cache_dir.glob('*.jpg'):
                try:
                    cache_file.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted cached thumbnail: {cache_file}")
                except OSError as e:
                    logger.warning(f"Failed to delete cache file {cache_file}: {e}")

            # Remove directory if empty
            try:
                thumb_cache_dir.rmdir()
            except OSError:
                pass  # Directory not empty or other error

        # Try to remove set directory if empty
        try:
            set_cache_key = f"{set_number}-{version_number}"
            full_cache_dir.parent.rmdir() if full_cache_dir.parent.name == set_cache_key else None
            thumb_cache_dir.parent.rmdir() if thumb_cache_dir.parent.name == set_cache_key else None
        except OSError:
            pass  # Directory not empty or other error

        logger.info(f"Set cache cleanup completed for {set_number}-{version_number}: {deleted_count} files deleted")
        return deleted_count

    except Exception as e:
        logger.error(f"Error during set cache cleanup for {set_number}-{version_number}: {e}")
        return 0


def clear_old_cache(max_age_days: int = 7) -> int:
    """
    Clear old cache files across all sets.
    Returns the number of files deleted.
    """
    try:
        base_cache_dir = get_peeron_cache_dir()
        if not base_cache_dir.exists():
            return 0

        deleted_count = 0
        max_age_seconds = max_age_days * 24 * 60 * 60
        current_time = time.time()

        # Clean both full and thumbs directories
        for cache_type in ['full', 'thumbs']:
            cache_type_dir = base_cache_dir / cache_type
            if cache_type_dir.exists():
                for set_dir in cache_type_dir.iterdir():
                    if set_dir.is_dir():
                        for cache_file in set_dir.glob('*.jpg'):
                            file_age = current_time - os.path.getmtime(cache_file)
                            if file_age > max_age_seconds:
                                try:
                                    cache_file.unlink()
                                    deleted_count += 1
                                    logger.debug(f"Deleted old cache file: {cache_file}")
                                except OSError as e:
                                    logger.warning(f"Failed to delete cache file {cache_file}: {e}")

                        # Remove empty directories
                        try:
                            if not any(set_dir.iterdir()):
                                set_dir.rmdir()
                        except OSError:
                            pass

        logger.info(f"Old cache cleanup completed: {deleted_count} files deleted")
        return deleted_count

    except Exception as e:
        logger.error(f"Error during old cache cleanup: {e}")
        return 0


class PeeronPage(NamedTuple):
    """Represents a single instruction page from Peeron"""
    page_number: str
    original_image_url: str           # Original Peeron full-size image URL
    cached_full_image_path: str       # Local full-size cached image path
    cached_thumbnail_url: str         # Local thumbnail URL for preview
    alt_text: str
    rotation: int = 0                 # Rotation in degrees (0, 90, 180, 270)


# Peeron instruction scraper
class PeeronInstructions(object):
    socket: 'BrickSocket | None'
    set_number: str
    version_number: str
    pages: list[PeeronPage]

    def __init__(
        self,
        set_number: str,
        version_number: str = '1',
        /,
        *,
        socket: 'BrickSocket | None' = None,
    ):
        # Save the socket
        self.socket = socket

        # Parse set number (handle both "4011" and "4011-1" formats)
        if '-' in set_number:
            parts = set_number.split('-', 1)
            self.set_number = parts[0]
            self.version_number = parts[1] if len(parts) > 1 else '1'
        else:
            self.set_number = set_number
            self.version_number = version_number

        # Placeholder for pages
        self.pages = []

    # Check if instructions exist on Peeron (lightweight)
    def exists(self, /) -> bool:
        """Check if the set exists on Peeron without caching thumbnails"""
        try:
            base_url = get_peeron_instruction_url(self.set_number, self.version_number)
            scraper = create_peeron_scraper()
            response = scraper.get(base_url)

            if response.status_code != 200:
                return False

            soup = BeautifulSoup(response.text, 'html.parser')

            # Check for "Browse instruction library" header (set not found)
            if soup.find('h1', string="Browse instruction library"):
                return False

            # Look for thumbnail images to confirm instructions exist
            thumbnails = soup.select('table[cellspacing="5"] a img[src^="http://belay.peeron.com/thumbs/"]')
            return len(thumbnails) > 0

        except Exception:
            return False

    # Find all available instruction pages on Peeron
    def find_pages(self, /) -> list[PeeronPage]:
        """
        Scrape Peeron's HTML and return a list of available instruction pages.
        Similar to BrickInstructions.find_instructions() but for Peeron.
        """
        base_url = get_peeron_instruction_url(self.set_number, self.version_number)
        thumb_base_url = get_peeron_thumbnail_url(self.set_number, self.version_number)
        scan_base_url = get_peeron_scan_url(self.set_number, self.version_number)

        logger.debug(f"[find_pages] fetching HTML from {base_url!r}")

        # Set up session with persistent cookies for Peeron (like working dl_peeron.py)
        scraper = create_peeron_scraper()

        # Download the main HTML page to establish session and cookies
        try:
            logger.debug(f"[find_pages] Establishing session by visiting: {base_url}")
            response = scraper.get(base_url)
            logger.debug(f"[find_pages] Main page visit: HTTP {response.status_code}")
            if response.status_code != 200:
                raise ErrorException(f'Failed to load Peeron page for {self.set_number}-{self.version_number}. HTTP {response.status_code}')
        except requests.exceptions.RequestException as e:
            raise ErrorException(f'Failed to connect to Peeron: {e}')

        # Parse HTML to locate instruction pages
        soup = BeautifulSoup(response.text, 'html.parser')

        # Check for "Browse instruction library" header (set not found)
        if soup.find('h1', string="Browse instruction library"):
            raise ErrorException(f'Set {self.set_number}-{self.version_number} not found on Peeron')

        # Locate all thumbnail images in the expected table structure
        # Use the configured thumbnail pattern to build the expected URL prefix
        thumb_base_url = get_peeron_thumbnail_url(self.set_number, self.version_number)
        thumbnails = soup.select(f'table[cellspacing="5"] a img[src^="{thumb_base_url}"]')

        if not thumbnails:
            raise ErrorException(f'No instruction pages found for {self.set_number}-{self.version_number} on Peeron')

        pages: list[PeeronPage] = []
        total_thumbnails = len(thumbnails)

        # Initialize progress if socket is available
        if self.socket:
            self.socket.progress_total = total_thumbnails
            self.socket.progress_count = 0
            self.socket.progress(message=f"Starting to cache {total_thumbnails} full images")

        for idx, img in enumerate(thumbnails, 1):
            thumb_url = img['src']

            # Extract the page number from the thumbnail URL
            page_number = thumb_url.split('/')[-2]

            # Build the full-size scan URL using the page number
            full_size_url = f"{scan_base_url}{page_number}/"

            logger.debug(f"[find_pages] Page {page_number}: thumb={thumb_url}, full_size={full_size_url}")

            # Create alt text for the page
            alt_text = f"LEGO Instructions {self.set_number}-{self.version_number} Page {page_number}"

            # Report progress if socket is available
            if self.socket:
                self.socket.progress_count = idx
                self.socket.progress(message=f"Caching full image {idx} of {total_thumbnails}")

            # Cache the full-size image and generate thumbnail preview using established session
            cached_full_path, cached_thumb_url = cache_full_image_and_generate_thumbnail(
                full_size_url, page_number, self.set_number, self.version_number, session=scraper
            )

            # Skip this page if caching failed
            if not cached_full_path or not cached_thumb_url:
                logger.warning(f"[find_pages] Skipping page {page_number} due to caching failure")
                continue

            page = PeeronPage(
                page_number=page_number,
                original_image_url=full_size_url,
                cached_full_image_path=cached_full_path,
                cached_thumbnail_url=cached_thumb_url,
                alt_text=alt_text
            )
            pages.append(page)

        # Cache the pages for later use
        self.pages = pages

        logger.debug(f"[find_pages] found {len(pages)} pages for {self.set_number}-{self.version_number}")
        return pages

    # Find instructions with fallback to Peeron
    @staticmethod
    def find_instructions_with_peeron_fallback(set: str, /) -> tuple[list[tuple[str, str]], list[PeeronPage] | None]:
        """
        Enhanced version of BrickInstructions.find_instructions() that falls back to Peeron.
        Returns (rebrickable_instructions, peeron_pages).
        If rebrickable_instructions is empty, peeron_pages will contain Peeron data.
        """
        from .instructions import BrickInstructions

        # First try Rebrickable
        try:
            rebrickable_instructions = BrickInstructions.find_instructions(set)
            return rebrickable_instructions, None
        except ErrorException as e:
            logger.info(f"Rebrickable failed for {set}: {e}. Trying Peeron fallback...")

            # Fallback to Peeron
            try:
                peeron = PeeronInstructions(set)
                peeron_pages = peeron.find_pages()
                return [], peeron_pages
            except ErrorException as peeron_error:
                # Both failed, re-raise original Rebrickable error
                logger.info(f"Peeron also failed for {set}: {peeron_error}")
                raise e from peeron_error