from typing import Any, Generic, Type, TypeVar, TYPE_CHECKING
import logging

from .bricklink_catalog import (
    BrickLinkCatalog,
    ITEM_TYPE_MINIFIGURE,
    ITEM_TYPE_PART,
    ITEM_TYPE_SET,
)
from .exceptions import ErrorException, NotFoundException
if TYPE_CHECKING:
    from .minifigure import BrickMinifigure
    from .part import BrickPart
    from .rebrickable_set import RebrickableSet
    from .set import BrickSet
    from .socket import BrickSocket
    from .wish import BrickWish

T = TypeVar('T', 'RebrickableSet', 'BrickPart', 'BrickMinifigure', 'BrickWish')

logger = logging.getLogger(__name__)


# Помощник вокруг каталога BrickLink, повторяющий форму прежней обёртки
# вокруг API Rebrickable: та же пара get() и list(), те же параметры на
# вызывающей стороне. Разница внутри — данные берутся из локального дампа,
# а не из сети, поэтому здесь нет ни ретраев, ни постраничного обхода.
class BrickLink(Generic[T]):
    operation: str
    identifier: str
    model: Type[T]

    brickset: 'BrickSet | None'
    instance: T | None
    minifigure: 'BrickMinifigure | None'
    socket: 'BrickSocket | None'

    OPERATIONS = (
        'get_set',
        'get_minifigure',
        'get_set_elements',
        'get_set_minifigs',
        'get_minifig_elements',
    )

    def __init__(
        self,
        operation: str,
        identifier: str,
        model: Type[T],
        /,
        *,
        brickset: 'BrickSet | None' = None,
        instance: T | None = None,
        minifigure: 'BrickMinifigure | None' = None,
        socket: 'BrickSocket | None' = None,
    ):
        if operation not in self.OPERATIONS:
            raise ErrorException('{operation} is not a valid BrickLink catalog operation'.format(  # noqa: E501
                operation=operation,
            ))

        self.operation = operation
        self.identifier = identifier
        self.model = model

        self.brickset = brickset
        self.instance = instance
        self.minifigure = minifigure
        self.socket = socket

    # Получить одну позицию
    def get(self, /) -> T:
        with BrickLinkCatalog() as catalog:
            if self.operation == 'get_set':
                data = self.load_set(catalog)
            else:
                data = self.load_minifigure(catalog)

        if self.instance is None:
            self.instance = self.model(**self.model_parameters())

        self.instance.ingest(self.model.from_bricklink(
            data,
            brickset=self.brickset,
        ))

        return self.instance

    # Получить список позиций
    def list(self, /) -> list[T]:
        with BrickLinkCatalog() as catalog:
            if self.operation == 'get_set_minifigs':
                records = self.load_set_minifigures(catalog)
            elif self.operation == 'get_set_elements':
                records = self.load_elements(catalog, ITEM_TYPE_SET)
            else:
                records = self.load_elements(catalog, ITEM_TYPE_MINIFIGURE)

        if self.socket is not None:
            self.socket.total_progress(len(records), add=True)

        model_parameters = self.model_parameters()

        return [
            self.model(
                **model_parameters,
                record=self.model.from_bricklink(
                    record,
                    brickset=self.brickset,
                    minifigure=self.minifigure,
                ),
            )
            for record in records
        ]

    # Параметры, передаваемые модели: только заданные, как это делала
    # прежняя обёртка — не всякая модель принимает оба
    def model_parameters(self, /) -> dict[str, Any]:
        parameters: dict[str, Any] = {}

        if self.brickset is not None:
            parameters['brickset'] = self.brickset

        if self.minifigure is not None:
            parameters['minifigure'] = self.minifigure

        return parameters

    # -- Чтение каталога --------------------------------------------------

    # Справочная запись о позиции
    #
    # Справочники большие: items/P.xml это 96 504 записи. Поэтому проход
    # делается один и сразу по всем нужным идентификаторам, а не по одному
    # на каждую деталь.
    @staticmethod
    def reference(
        catalog: BrickLinkCatalog,
        item_type: str,
        wanted: set[str],
        /,
    ) -> dict[str, dict[str, str]]:
        if not wanted:
            return {}

        found: dict[str, dict[str, str]] = {}

        for item in catalog.items(item_type):
            if item['ITEMID'] in wanted:
                found[item['ITEMID']] = item

                # Ранний выход: справочник перебирать дальше незачем
                if len(found) == len(wanted):
                    break

        return found

    # Цвета, разложенные по идентификатору
    @staticmethod
    def colors(catalog: BrickLinkCatalog, /) -> dict[int, dict[str, str]]:
        return {int(color['COLOR']): color for color in catalog.colors()}

    # Набор
    def load_set(self, catalog: BrickLinkCatalog, /) -> dict[str, Any]:
        item = self.reference(
            catalog,
            ITEM_TYPE_SET,
            {self.identifier},
        ).get(self.identifier)

        if item is None:
            raise NotFoundException('Set {set} was not found in the BrickLink catalog'.format(  # noqa: E501
                set=self.identifier,
            ))

        inventory = catalog.inventory(ITEM_TYPE_SET, self.identifier) or []

        # Rebrickable отдавал число деталей готовым, здесь его надо
        # посчитать. Запасные и производные позиции не в счёт: первые не
        # входят в сборку, вторые лишь вид уже посчитанной детали.
        item['NUMBER_OF_PARTS'] = str(sum(
            entry['quantity']
            for entry in inventory
            if entry['item_type'] == ITEM_TYPE_PART
            and not entry['extra']
            and not entry['counterpart']
        ))

        return item

    # Фигурка
    def load_minifigure(self, catalog: BrickLinkCatalog, /) -> dict[str, Any]:
        item = self.reference(
            catalog,
            ITEM_TYPE_MINIFIGURE,
            {self.identifier},
        ).get(self.identifier)

        if item is None:
            raise NotFoundException('Minifigure {figure} was not found in the BrickLink catalog'.format(  # noqa: E501
                figure=self.identifier,
            ))

        item['QTY'] = '1'

        # Число деталей фигурки в справочнике не хранится
        inventory = catalog.inventory(
            ITEM_TYPE_MINIFIGURE,
            self.identifier,
        ) or []

        item['NUMBER_OF_PARTS'] = str(sum(
            entry['quantity']
            for entry in inventory
            if entry['item_type'] == ITEM_TYPE_PART
            and not entry['extra']
            and not entry['counterpart']
        ))

        return item

    # Фигурки набора
    def load_set_minifigures(
        self,
        catalog: BrickLinkCatalog,
        /,
    ) -> list[dict[str, Any]]:
        inventory = catalog.inventory(ITEM_TYPE_SET, self.identifier)

        if inventory is None:
            raise NotFoundException('Set {set} has no inventory in the BrickLink catalog'.format(  # noqa: E501
                set=self.identifier,
            ))

        entries = [
            entry for entry in inventory
            if entry['item_type'] == ITEM_TYPE_MINIFIGURE
        ]

        reference = self.reference(
            catalog,
            ITEM_TYPE_MINIFIGURE,
            {entry['item'] for entry in entries},
        )

        records: list[dict[str, Any]] = []

        for entry in entries:
            item = dict(reference.get(entry['item'], {}))
            item.setdefault('ITEMID', entry['item'])
            item['QTY'] = str(entry['quantity'])
            records.append(item)

        return records

    # Детали набора или фигурки
    def load_elements(
        self,
        catalog: BrickLinkCatalog,
        item_type: str,
        /,
    ) -> list[dict[str, Any]]:
        inventory = catalog.inventory(item_type, self.identifier)

        if inventory is None:
            raise NotFoundException('{identifier} has no inventory in the BrickLink catalog'.format(  # noqa: E501
                identifier=self.identifier,
            ))

        entries = [
            entry for entry in inventory
            if entry['item_type'] == ITEM_TYPE_PART
        ]

        reference = self.reference(
            catalog,
            ITEM_TYPE_PART,
            {entry['item'] for entry in entries},
        )
        colors = self.colors(catalog)

        records: list[dict[str, Any]] = []

        for entry in entries:
            record = dict(entry)
            record['reference'] = reference.get(entry['item'], {})
            record['color_reference'] = colors.get(entry['color'], {})
            records.append(record)

        return records
