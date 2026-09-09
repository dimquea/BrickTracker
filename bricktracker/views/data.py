import os
import logging
from flask import Blueprint, current_app, send_from_directory, abort
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

data_page = Blueprint(
    'data',
    __name__,
    url_prefix='/data'
)


@data_page.route('/<path:folder>/<filename>')
def serve_data_file(folder: str, filename: str):
    """
    Serve files from the data folder (images, PDFs, etc.)
    This replaces serving these files from static/ folder.

    Security:
    - Only allows serving files from configured data folders
    - Uses secure_filename to prevent path traversal
    - Returns 404 if file doesn't exist or folder not allowed
    """
    # Secure the filename to prevent path traversal attacks
    safe_filename = secure_filename(filename)

    # Get the configured data folders
    allowed_folders = {
        'sets': current_app.config.get('SETS_FOLDER', './data/sets'),
        'parts': current_app.config.get('PARTS_FOLDER', './data/parts'),
        'minifigures': current_app.config.get('MINIFIGURES_FOLDER', './data/minifigures'),
        'instructions': current_app.config.get('INSTRUCTIONS_FOLDER', './data/instructions'),
        'lots': current_app.config.get('LOTS_FOLDER', './data/lots'),
    }

    # Check if the requested folder is allowed
    if folder not in allowed_folders:
        logger.warning(f"Attempt to access unauthorized folder: {folder}")
        abort(404)

    # Get the actual folder path
    folder_path = allowed_folders[folder]

    # If folder_path is relative (not absolute), make it relative to app root
    if not os.path.isabs(folder_path):
        folder_path = os.path.join(current_app.root_path, folder_path)

    # Check if file exists
    file_path = os.path.join(folder_path, safe_filename)
    if not os.path.isfile(file_path):
        logger.warning(f"File not found: {file_path} (configured folder: {folder_path})")
        abort(404)

    # Verify the resolved path is still within the allowed folder (security check)
    if not os.path.abspath(file_path).startswith(os.path.abspath(folder_path)):
        logger.warning(f"Path traversal attempt detected: {filename}")
        abort(404)

    return send_from_directory(folder_path, safe_filename)
