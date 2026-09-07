from datetime import datetime, timezone
import logging
import os

from flask import current_app, g
import humanize

from .bricklink_catalog import BrickLinkCatalog
from .theme import BrickTheme

logger = logging.getLogger(__name__)


# Lego sets themes
class BrickThemeList(object):
    themes: dict[int, BrickTheme]
    mtime: datetime | None
    size: int | None
    exception: Exception | None

    def __init__(self, /, *, force: bool = False):
        # Load themes only if there is none already loaded
        themes = getattr(self, 'themes', None)

        if themes is None or force:
            logger.info('Loading themes list')

            BrickThemeList.themes = {}

            # Темы теперь берутся из категорий каталога BrickLink.
            # Иерархии у них нет, в отличие от тем Rebrickable, поэтому
            # родитель всегда пуст: дерево вырождается в плоский список,
            # но фильтры и статистика работают как прежде.
            try:
                path = current_app.config['BRICKLINK_CATALOG_PATH']

                with BrickLinkCatalog() as catalog:
                    for category in catalog.categories():
                        theme = BrickTheme(
                            int(category['CATEGORY']),
                            category['CATEGORYNAME'],
                        )
                        BrickThemeList.themes[theme.id] = theme

                # File stats
                stat = os.stat(path)
                BrickThemeList.size = stat.st_size
                BrickThemeList.mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)  # noqa: E501

                BrickThemeList.exception = None

            # Ignore errors
            except Exception as e:
                BrickThemeList.exception = e
                BrickThemeList.size = None
                BrickThemeList.mtime = None

    # Get a theme
    def get(self, id: int, /) -> BrickTheme:
        # Seed a fake entry if missing
        if id not in self.themes:
            BrickThemeList.themes[id] = BrickTheme(
                id,
                'Unknown ({id})'.format(id=id)
            )

        return self.themes[id]

    # Display the size in a human format
    def human_size(self) -> str:
        if self.size is not None:
            return humanize.naturalsize(self.size)
        else:
            return ''

    # Display the time in a human format
    def human_time(self) -> str:
        if self.mtime is not None:
            return self.mtime.astimezone(g.timezone).strftime(
                current_app.config['FILE_DATETIME_FORMAT']
            )
        else:
            return ''

    # Update the file
    #
    # Категории живут внутри каталога, отдельного файла тем больше нет,
    # поэтому обновляется каталог целиком.
    @staticmethod
    def update() -> None:
        BrickLinkCatalog.update()

        logger.info('Theme list updated')
