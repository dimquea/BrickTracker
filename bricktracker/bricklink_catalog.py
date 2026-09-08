from datetime import datetime, timezone
from typing import Any, Iterator
from xml.etree import ElementTree
import json
import logging
import os
import time
import zipfile

from flask import current_app, g
import humanize
import requests

from .exceptions import (
    ConfigurationMissingException,
    ErrorException,
    NotFoundException,
)

logger = logging.getLogger(__name__)

# Типы позиций каталога BrickLink
ITEM_TYPE_PART = 'P'
ITEM_TYPE_SET = 'S'
ITEM_TYPE_MINIFIGURE = 'M'

# Справочники внутри архива
COLORS_FILE = 'colors.xml'
CATEGORIES_FILE = 'categories.xml'
ITEM_TYPES_FILE = 'itemtypes.xml'

DOWNLOAD_TIMEOUT = 60
DOWNLOAD_CHUNK = 1 << 16

# Поля справочника, которые кто-либо читает. Остальные (ALTITEMIDS,
# ITEMWEIGHT, IMAGECOLOR) в индекс не попадают: он и так самое тяжёлое,
# что приложение держит в памяти.
INDEX_FIELDS = ('ITEMNAME', 'CATEGORY', 'ITEMYEAR')

# Как часто разбор справочника уступает управление и на сколько
#
# Пауза именно ненулевая: gevent.sleep(0) переключается только между
# готовыми greenlet-ами, а тот, которым gunicorn отмечается живым, ждёт
# таймера. Чтобы таймеры прокрутились, hub должен пройти полный оборот.
INDEX_YIELD_EVERY = 5000
INDEX_YIELD_SECONDS = 0.001

# Разобранные справочники, общие на процесс. Ключ включает приметы файла,
# поэтому после update() индекс собирается заново, а не отдаёт старое.
_INDEX: dict[tuple[Any, ...], dict[str, tuple[str, ...]]] = {}

# Открытый архив, общий на процесс, с тем же ключом
_ARCHIVE: dict[tuple[Any, ...], zipfile.ZipFile] = {}


# Адрес картинки позиции
#
# BrickLink не отдаёт адреса изображений в выгрузке: они складываются из
# типа позиции, цвета и артикула. Для наборов и фигурок цвет нулевой.
def image_url(item_type: str, item: str, /, *, color: int = 0) -> str:
    return current_app.config['BRICKLINK_IMAGE_PATTERN'].format(
        type=item_type,
        color=color,
        item=item,
    )


# Имя файла в локальном кэше изображений
#
# У детали картинка своя для каждого цвета, поэтому цвет входит в имя.
def image_name(
    item_type: str,
    item: str,
    /,
    *,
    color: int | None = None,
) -> str:
    if color is None:
        return item

    return '{item}_{color}'.format(item=item, color=color)


# Потребовать наличие каталога
#
# Пришло на смену проверке ключа Rebrickable на страницах, откуда
# добавляют наборы: ключа больше нет, а без каталога добавлять нечего.
def error_unless_catalog() -> None:
    if not BrickLinkCatalog().exists():
        # Именно ConfigurationMissingException, а не NotFoundException:
        # страница существует, не хватает предусловия. Такой же тип
        # использовался прежней проверкой ключа Rebrickable, и он даёт
        # понятную страницу вместо 404.
        raise ConfigurationMissingException('The BrickLink catalog has not been downloaded yet. Update it from the admin page.')  # noqa: E501


# Каталог BrickLink, читаемый из архива выгрузок.
#
# Архив собирает и публикует проект brickstore-database: это официальные
# выгрузки BrickLink, пересобираемые ежечасно. Мы берём готовый релиз, а не
# ходим в API BrickLink, поэтому здесь нет ни ключей, ни OAuth, ни лимитов.
#
# Инвентари читаются по одному члену прямо из архива: распакованный он весит
# больше полугигабайта и содержит около 53 000 файлов, а на устройстве с Home
# Assistant это заметно.
class BrickLinkCatalog(object):
    path: str

    def __init__(self, /, *, path: str | None = None):
        if path is None:
            path = current_app.config['BRICKLINK_CATALOG_PATH']

        self.path = path

    # Архив общий на процесс и живёт до подмены файла, так что закрывать
    # экземпляру нечего. Менеджер контекста оставлен: вызывающий код им
    # размечает работу с каталогом, и читать его так понятнее.
    def __enter__(self, /) -> 'BrickLinkCatalog':
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def close(self, /) -> None:
        pass

    # -- Файл каталога ----------------------------------------------------

    # Есть ли скачанный каталог
    def exists(self, /) -> bool:
        return os.path.isfile(self.path)

    # Размер файла в человеческом виде
    def human_size(self, /) -> str:
        if not self.exists():
            return ''

        return humanize.naturalsize(os.stat(self.path).st_size)

    # Время последнего обновления в человеческом виде
    def human_time(self, /) -> str:
        if not self.exists():
            return ''

        mtime = datetime.fromtimestamp(
            os.stat(self.path).st_mtime,
            tz=timezone.utc,
        )

        return mtime.astimezone(g.timezone).strftime(
            current_app.config['FILE_DATETIME_FORMAT']
        )

    # Скачать свежий каталог
    #
    # По умолчанию берётся последний релиз brickstore-database, но прямой
    # адрес можно задать через BRICKLINK_CATALOG_URL. Источник намеренно
    # сделан настраиваемым: репозиторий личный, и если он исчезнет, подменить
    # адрес должно быть можно без правки кода.
    @staticmethod
    def update() -> None:
        url = current_app.config['BRICKLINK_CATALOG_URL']

        if not url:
            url = BrickLinkCatalog.resolve_release_asset()

        path = current_app.config['BRICKLINK_CATALOG_PATH']
        temporary_path = '{path}.part'.format(path=path)

        logger.info('Downloading the BrickLink catalog from {url}'.format(
            url=url,
        ))

        try:
            response = requests.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT)

            if not response.ok:
                raise ErrorException('An error occured while downloading the BrickLink catalog ({code})'.format(  # noqa: E501
                    code=response.status_code,
                ))

            # Пишем через временный файл: оборванная загрузка не должна
            # оставить битый архив на месте рабочего.
            with open(temporary_path, 'wb') as f:
                for chunk in response.iter_content(DOWNLOAD_CHUNK):
                    f.write(chunk)

            # Проверяем, что скачалось нечто читаемое, до подмены
            with zipfile.ZipFile(temporary_path) as archive:
                if archive.testzip() is not None:
                    raise ErrorException('The downloaded BrickLink catalog is corrupted')  # noqa: E501

            os.replace(temporary_path, path)

        except Exception:
            try:
                os.remove(temporary_path)
            except OSError:
                pass

            raise

        logger.info('BrickLink catalog updated')

    # Найти адрес архива в последнем релизе
    @staticmethod
    def resolve_release_asset() -> str:
        release_url = current_app.config['BRICKLINK_CATALOG_RELEASE_URL']
        asset_name = current_app.config['BRICKLINK_CATALOG_ASSET']

        response = requests.get(release_url, timeout=DOWNLOAD_TIMEOUT)

        if not response.ok:
            raise ErrorException('An error occured while looking up the BrickLink catalog release ({code})'.format(  # noqa: E501
                code=response.status_code,
            ))

        try:
            release = json.loads(response.content)
        except ValueError as e:
            raise ErrorException('Could not read the BrickLink catalog release: {error}'.format(  # noqa: E501
                error=e,
            ))

        for asset in release.get('assets', []):
            if asset.get('name') == asset_name:
                return asset['browser_download_url']

        raise NotFoundException('No asset named {name} in the BrickLink catalog release'.format(  # noqa: E501
            name=asset_name,
        ))

    # -- Чтение архива ----------------------------------------------------

    # Открыть архив
    #
    # Открытый архив общий на процесс: в нём около 53 000 записей, и разбор
    # оглавления стоит порядка секунды. Экземпляр создаётся на каждое
    # обращение к каталогу, то есть на каждую фигурку набора, так что
    # секунда набегала двадцать семь раз подряд.
    #
    # Ключ тот же, что у справочника: после update() файл подменяется, и
    # прежний архив закрывается, а не отдаётся дальше.
    def archive(self, /) -> zipfile.ZipFile:
        if not self.exists():
            raise NotFoundException('The BrickLink catalog has not been downloaded yet')  # noqa: E501

        key = self.signature()

        opened = _ARCHIVE.get(key)

        if opened is not None:
            return opened

        for stale_key, stale in list(_ARCHIVE.items()):
            stale.close()
            del _ARCHIVE[stale_key]

        try:
            opened = zipfile.ZipFile(self.path)
        except zipfile.BadZipFile as e:
            raise ErrorException('The BrickLink catalog is not readable: {error}'.format(  # noqa: E501
                error=e,
            ))

        _ARCHIVE[key] = opened

        return opened

    # Разобрать один член архива в список записей
    #
    # Разбор потоковый: items/P.xml весит 32 МБ, и держать его целиком в
    # памяти незачем.
    def parse(self, name: str, /) -> Iterator[dict[str, str]]:
        try:
            member = self.archive().open(name)
        except KeyError:
            raise NotFoundException('{name} is missing from the BrickLink catalog'.format(  # noqa: E501
                name=name,
            ))

        with member:
            for _, element in ElementTree.iterparse(member):
                if element.tag != 'ITEM':
                    continue

                yield {
                    child.tag: (child.text or '').strip()
                    for child in element
                }

                # Иначе разобранное дерево копится в памяти
                element.clear()

    # Цвета
    def colors(self, /) -> Iterator[dict[str, str]]:
        return self.parse(COLORS_FILE)

    # Категории
    def categories(self, /) -> Iterator[dict[str, str]]:
        return self.parse(CATEGORIES_FILE)

    # Типы позиций
    def item_types(self, /) -> Iterator[dict[str, str]]:
        return self.parse(ITEM_TYPES_FILE)

    # Справочник позиций одного типа
    def items(self, item_type: str, /) -> Iterator[dict[str, str]]:
        return self.parse('items/{type}.xml'.format(type=item_type))

    # Приметы файла каталога: по ним индекс понимает, что архив сменился
    def signature(self, /) -> tuple[Any, ...]:
        stat = os.stat(self.path)

        return (self.path, stat.st_size, stat.st_mtime_ns)

    # Справочник позиций одного типа, разобранный один раз на процесс
    #
    # items/P.xml — это 96 504 записи и около пяти секунд разбора. Раньше
    # он читался заново на каждый поиск, то есть на каждую фигурку набора:
    # у 10188-1 с его 27 фигурками набегало под три минуты сплошного
    # разбора, и gunicorn успевал убить воркера по таймауту раньше, чем
    # набор дочитывался.
    #
    # Плата — около 40 МБ памяти на справочник деталей, которые процесс
    # держит до перезапуска. Меньше было бы только с индексом на диске, но
    # он попал бы в резервную копию базы, а она и так не маленькая.
    def index(self, item_type: str, /) -> dict[str, tuple[str, ...]]:
        key = self.signature() + (item_type,)

        cached = _INDEX.get(key)

        if cached is not None:
            return cached

        # Архив сменился: разобранное по прежнему файлу больше не нужно
        for stale in [k for k in _INDEX if k[:-1] != key[:-1]]:
            del _INDEX[stale]

        logger.debug('Indexing BrickLink catalog items of type {type}'.format(
            type=item_type,
        ))

        index: dict[str, tuple[str, ...]] = {}

        for number, item in enumerate(self.items(item_type), start=1):
            index[item['ITEMID']] = tuple(
                item.get(field, '') for field in INDEX_FIELDS
            )

            # Уступаем управление циклу gevent
            #
            # Разбор справочника деталей — это несколько секунд подряд без
            # единой точки переключения, а на медленном железе и десятки.
            # Всё это время greenlet, которым gunicorn отмечается живым, не
            # получает управления. Под gevent time.sleep пропатчен и
            # переключает задачи, без него это короткая пауза.
            if number % INDEX_YIELD_EVERY == 0:
                time.sleep(INDEX_YIELD_SECONDS)

        _INDEX[key] = index

        return index

    # Справочная запись об одной позиции
    #
    # Словарь собирается заново на каждое обращение: вызывающие дописывают
    # в него своё (NUMBER_OF_PARTS, QTY), и общий на всех экземпляр они бы
    # испортили.
    def item(self, item_type: str, item_id: str, /) -> dict[str, str] | None:
        entry = self.index(item_type).get(item_id)

        if entry is None:
            return None

        found = {'ITEMTYPE': item_type, 'ITEMID': item_id}
        found.update(zip(INDEX_FIELDS, entry))

        return found

    # Инвентарь позиции: состав набора, фигурки или сборной детали
    #
    # Возвращает None, если у позиции инвентаря нет — это нормально и для
    # набора, и для фигурки.
    def inventory(
        self,
        item_type: str,
        item_id: str,
        /,
    ) -> list[dict[str, Any]] | None:
        name = '{type}/{id}.xml'.format(type=item_type, id=item_id)

        try:
            self.archive().getinfo(name)
        except KeyError:
            return None

        return [
            {
                'item_type': item['ITEMTYPE'],
                'item': item['ITEMID'],
                'color': int(item['COLOR']),
                'quantity': int(item['QTY']),
                # Запасные детали
                'extra': item['EXTRA'] == 'Y',
                # Альтернативы группируются между собой по match_id
                'alternate': item['ALTERNATE'] == 'Y',
                'match_id': int(item['MATCHID']),
                # Деталь, получающаяся применением наклейки или сборкой:
                # не отдельная физическая деталь, а вид уже учтённой
                'counterpart': item['COUNTERPART'] == 'Y',
            }
            for item in self.parse(name)
        ]
