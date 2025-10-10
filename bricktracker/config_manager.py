import os
import logging
from typing import Any, Dict, Final, List, Optional
from pathlib import Path
from flask import current_app

logger = logging.getLogger(__name__)

# Environment variables that can be changed live without restart
LIVE_CHANGEABLE_VARS: Final[List[str]] = [
    'BK_BRICKLINK_LINKS',
    'BK_DEFAULT_TABLE_PER_PAGE',
    'BK_DESCRIPTION_BADGE_MAX_LENGTH',
    'BK_INDEPENDENT_ACCORDIONS',
    'BK_HIDE_ADD_SET',
    'BK_HIDE_ADD_BULK_SET',
    'BK_HIDE_ADMIN',
    'BK_ADMIN_DEFAULT_EXPANDED_SECTIONS',
    'BK_HIDE_ALL_INSTRUCTIONS',
    'BK_HIDE_ALL_MINIFIGURES',
    'BK_HIDE_ALL_PARTS',
    'BK_HIDE_ALL_PROBLEMS_PARTS',
    'BK_HIDE_ALL_SETS',
    'BK_HIDE_ALL_STORAGES',
    'BK_HIDE_STATISTICS',
    'BK_HIDE_SET_INSTRUCTIONS',
    'BK_HIDE_TABLE_DAMAGED_PARTS',
    'BK_HIDE_TABLE_MISSING_PARTS',
    'BK_HIDE_TABLE_CHECKED_PARTS',
    'BK_HIDE_WISHES',
    'BK_MINIFIGURES_PAGINATION_SIZE_DESKTOP',
    'BK_MINIFIGURES_PAGINATION_SIZE_MOBILE',
    'BK_MINIFIGURES_SERVER_SIDE_PAGINATION',
    'BK_PARTS_PAGINATION_SIZE_DESKTOP',
    'BK_PARTS_PAGINATION_SIZE_MOBILE',
    'BK_PARTS_SERVER_SIDE_PAGINATION',
    'BK_SETS_SERVER_SIDE_PAGINATION',
    'BK_PROBLEMS_PAGINATION_SIZE_DESKTOP',
    'BK_PROBLEMS_PAGINATION_SIZE_MOBILE',
    'BK_PROBLEMS_SERVER_SIDE_PAGINATION',
    'BK_SETS_PAGINATION_SIZE_DESKTOP',
    'BK_SETS_PAGINATION_SIZE_MOBILE',
    'BK_SETS_CONSOLIDATION',
    'BK_RANDOM',
    'BK_REBRICKABLE_LINKS',
    'BK_SHOW_GRID_FILTERS',
    'BK_SHOW_GRID_SORT',
    'BK_SHOW_SETS_DUPLICATE_FILTER',
    'BK_SKIP_SPARE_PARTS',
    'BK_USE_REMOTE_IMAGES',
    'BK_PEERON_DOWNLOAD_DELAY',
    'BK_PEERON_MIN_IMAGE_SIZE',
    'BK_REBRICKABLE_PAGE_SIZE',
    'BK_STATISTICS_SHOW_CHARTS',
    'BK_STATISTICS_DEFAULT_EXPANDED',
    # Default ordering and formatting
    'BK_INSTRUCTIONS_ALLOWED_EXTENSIONS',
    'BK_MINIFIGURES_DEFAULT_ORDER',
    'BK_PARTS_DEFAULT_ORDER',
    'BK_SETS_DEFAULT_ORDER',
    'BK_PURCHASE_LOCATION_DEFAULT_ORDER',
    'BK_STORAGE_DEFAULT_ORDER',
    'BK_WISHES_DEFAULT_ORDER',
    # URL and Pattern Variables
    'BK_BRICKLINK_LINK_PART_PATTERN',
    'BK_BRICKLINK_LINK_SET_PATTERN',
    'BK_REBRICKABLE_IMAGE_NIL',
    'BK_REBRICKABLE_IMAGE_NIL_MINIFIGURE',
    'BK_REBRICKABLE_LINK_MINIFIGURE_PATTERN',
    'BK_REBRICKABLE_LINK_PART_PATTERN',
    'BK_REBRICKABLE_LINK_INSTRUCTIONS_PATTERN',
    'BK_PEERON_INSTRUCTION_PATTERN',
    'BK_PEERON_SCAN_PATTERN',
    'BK_PEERON_THUMBNAIL_PATTERN',
    'BK_RETIRED_SETS_FILE_URL',
    'BK_RETIRED_SETS_PATH',
    'BK_THEMES_FILE_URL',
    'BK_THEMES_PATH'
]

# Environment variables that require restart
RESTART_REQUIRED_VARS: Final[List[str]] = [
    'BK_AUTHENTICATION_PASSWORD',
    'BK_AUTHENTICATION_KEY',
    'BK_DATABASE_PATH',
    'BK_DEBUG',
    'BK_DOMAIN_NAME',
    'BK_HOST',
    'BK_PORT',
    'BK_SOCKET_NAMESPACE',
    'BK_SOCKET_PATH',
    'BK_NO_THREADED_SOCKET',
    'BK_TIMEZONE',
    'BK_REBRICKABLE_API_KEY',
    'BK_INSTRUCTIONS_FOLDER',
    'BK_PARTS_FOLDER',
    'BK_SETS_FOLDER',
    'BK_MINIFIGURES_FOLDER',
    'BK_DATABASE_TIMESTAMP_FORMAT',
    'BK_FILE_DATETIME_FORMAT',
    'BK_PURCHASE_DATE_FORMAT',
    'BK_PURCHASE_CURRENCY',
    'BK_REBRICKABLE_USER_AGENT',
    'BK_USER_AGENT'
]

class ConfigManager:
    """Manages live configuration updates for BrickTracker"""

    def __init__(self):
        self.env_file_path = Path('.env')

    def get_current_config(self) -> Dict[str, Any]:
        """Get current configuration values for live-changeable variables"""
        config = {}
        for var in LIVE_CHANGEABLE_VARS:
            # Get internal config name
            internal_name = var.replace('BK_', '')
            # Get current value from Flask config
            if internal_name in current_app.config:
                config[var] = current_app.config[internal_name]
            else:
                # Fallback to environment variable
                config[var] = os.environ.get(var, '')
        return config

    def get_restart_required_config(self) -> Dict[str, Any]:
        """Get current configuration values for restart-required variables"""
        config = {}
        for var in RESTART_REQUIRED_VARS:
            # Get internal config name
            internal_name = var.replace('BK_', '')
            # Get current value from Flask config
            if internal_name in current_app.config:
                config[var] = current_app.config[internal_name]
            else:
                # Fallback to environment variable
                config[var] = os.environ.get(var, '')
        return config

    def update_config(self, updates: Dict[str, Any]) -> Dict[str, str]:
        """Update configuration values. Returns dict with status for each update"""
        results = {}
        for var_name, new_value in updates.items():
            if var_name not in LIVE_CHANGEABLE_VARS:
                results[var_name] = f"Error: {var_name} requires restart to change"
                continue

            try:
                # Update environment variable
                os.environ[var_name] = str(new_value)
                # Update Flask config
                internal_name = var_name.replace('BK_', '')
                cast_value = self._cast_value(var_name, new_value)
                current_app.config[internal_name] = cast_value
                # Update .env file
                self._update_env_file(var_name, new_value)
                results[var_name] = "Updated successfully"
                if current_app.debug:
                    logger.info(f"Config updated: {var_name}={new_value}")
            except Exception as e:
                results[var_name] = f"Error: {str(e)}"
                logger.error(f"Failed to update {var_name}: {e}")
        return results

    def _cast_value(self, var_name: str, value: Any) -> Any:
        """Cast value to appropriate type based on variable name"""
        # List variables (admin sections) - Check this FIRST before boolean check
        if 'sections' in var_name.lower():
            if isinstance(value, str):
                return [section.strip() for section in value.split(',') if section.strip()]
            elif isinstance(value, list):
                return value
            else:
                return []
        # Integer variables (pagination sizes, delays, etc.) - Check BEFORE boolean check
        if any(keyword in var_name.lower() for keyword in ['_size', '_page', 'delay', 'min_', 'per_page', 'page_size', '_length']):
            try:
                return int(value)
            except (ValueError, TypeError):
                return 0
        # Boolean variables - More specific patterns to avoid conflicts
        if any(keyword in var_name.lower() for keyword in ['hide_', 'server_side_pagination', '_links', 'random', 'skip_', 'show_', 'use_', '_consolidation', '_charts', '_expanded']):
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'on')
            return bool(value)
        # String variables (default)
        return str(value)

    def _format_env_value(self, value: Any) -> str:
        """Format value for .env file storage"""
        if isinstance(value, bool):
            return 'true' if value else 'false'
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, list):
            return ','.join(str(item) for item in value)
        elif value is None:
            return ''
        else:
            return str(value)

    def _update_env_file(self, var_name: str, value: Any) -> None:
        """Update the .env file with new value"""
        if not self.env_file_path.exists():
            self.env_file_path.touch()

        # Read current .env content
        lines = []
        if self.env_file_path.exists():
            with open(self.env_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

        # Format value for .env file
        env_value = self._format_env_value(value)

        # Find and update the line, or add new line
        updated = False

        # First pass: Look for existing active variable
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{var_name}="):
                lines[i] = f"{var_name}={env_value}\n"
                updated = True
                break

        # Second pass: If not found, look for commented-out variable
        if not updated:
            for i, line in enumerate(lines):
                stripped = line.strip()
                # Check for commented-out variable: # BK_VAR= or #BK_VAR=
                if stripped.startswith('#') and var_name in stripped:
                    # Extract the part after #, handling optional space
                    comment_content = stripped[1:].strip()
                    if comment_content.startswith(f"{var_name}=") or comment_content.startswith(f"{var_name} ="):
                        # Uncomment and set new value, preserving any leading whitespace from original line
                        leading_whitespace = line[:len(line) - len(line.lstrip())]
                        lines[i] = f"{leading_whitespace}{var_name}={env_value}\n"
                        updated = True
                        logger.info(f"Uncommented and updated {var_name} in .env file")
                        break

        # Third pass: If still not found, append to end
        if not updated:
            lines.append(f"{var_name}={env_value}\n")
            logger.info(f"Added new {var_name} to end of .env file")

        # Write back to file
        with open(self.env_file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

    def validate_config(self) -> Dict[str, Any]:
        """Validate current configuration"""
        issues = []
        warnings = []

        # Check if critical variables are set
        if not os.environ.get('BK_REBRICKABLE_API_KEY'):
            warnings.append("BK_REBRICKABLE_API_KEY not set - some features may not work")

        # Check for conflicting settings
        if (os.environ.get('BK_PARTS_SERVER_SIDE_PAGINATION', '').lower() == 'false' and
            int(os.environ.get('BK_PARTS_PAGINATION_SIZE_DESKTOP', '10')) > 100):
            warnings.append("Large pagination size with client-side pagination may cause performance issues")

        # Check pagination sizes are reasonable
        for var in ['BK_SETS_PAGINATION_SIZE_DESKTOP', 'BK_PARTS_PAGINATION_SIZE_DESKTOP', 'BK_MINIFIGURES_PAGINATION_SIZE_DESKTOP']:
            try:
                size = int(os.environ.get(var, '10'))
                if size < 1:
                    issues.append(f"{var} must be at least 1")
                elif size > 1000:
                    warnings.append(f"{var} is very large ({size}) - may cause performance issues")
            except ValueError:
                issues.append(f"{var} must be a valid integer")

        return {
            'issues': issues,
            'warnings': warnings,
            'status': 'valid' if not issues else 'has_issues'
        }

    def get_variable_help(self, var_name: str) -> str:
        """Get help text for a configuration variable"""
        help_text = {
            'BK_BRICKLINK_LINKS': 'Show BrickLink links throughout the application',
            'BK_DEFAULT_TABLE_PER_PAGE': 'Default number of items per page in tables',
            'BK_INDEPENDENT_ACCORDIONS': 'Make accordion sections independent (can open multiple)',
            'BK_HIDE_ADD_SET': 'Hide the "Add Set" menu entry',
            'BK_HIDE_ADD_BULK_SET': 'Hide the "Add Bulk Set" menu entry',
            'BK_HIDE_ADMIN': 'Hide the "Admin" menu entry',
            'BK_ADMIN_DEFAULT_EXPANDED_SECTIONS': 'Admin sections to expand by default (comma-separated)',
            'BK_HIDE_ALL_INSTRUCTIONS': 'Hide the "Instructions" menu entry',
            'BK_HIDE_ALL_MINIFIGURES': 'Hide the "Minifigures" menu entry',
            'BK_HIDE_ALL_PARTS': 'Hide the "Parts" menu entry',
            'BK_HIDE_ALL_PROBLEMS_PARTS': 'Hide the "Problems" menu entry',
            'BK_HIDE_ALL_SETS': 'Hide the "Sets" menu entry',
            'BK_HIDE_ALL_STORAGES': 'Hide the "Storages" menu entry',
            'BK_HIDE_STATISTICS': 'Hide the "Statistics" menu entry',
            'BK_HIDE_SET_INSTRUCTIONS': 'Hide instructions section in set details',
            'BK_HIDE_TABLE_DAMAGED_PARTS': 'Hide the "Damaged" column in parts tables',
            'BK_HIDE_TABLE_MISSING_PARTS': 'Hide the "Missing" column in parts tables',
            'BK_HIDE_TABLE_CHECKED_PARTS': 'Hide the "Checked" column in parts tables',
            'BK_HIDE_WISHES': 'Hide the "Wishes" menu entry',
            'BK_SETS_CONSOLIDATION': 'Enable set consolidation/grouping functionality',
            'BK_SHOW_GRID_FILTERS': 'Show filter options on grids by default',
            'BK_SHOW_GRID_SORT': 'Show sort options on grids by default',
            'BK_SKIP_SPARE_PARTS': 'Skip spare parts when importing sets',
            'BK_USE_REMOTE_IMAGES': 'Use remote images from Rebrickable CDN instead of local',
            'BK_STATISTICS_SHOW_CHARTS': 'Show collection growth charts on statistics page',
            'BK_STATISTICS_DEFAULT_EXPANDED': 'Expand all statistics sections by default'
        }
        return help_text.get(var_name, 'No help available for this variable')