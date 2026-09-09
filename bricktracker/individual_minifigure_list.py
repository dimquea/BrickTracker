import logging
from typing import Self

from .individual_minifigure import IndividualMinifigure
from .record_list import BrickRecordList
from .set_owner_list import BrickSetOwnerList
from .set_status_list import BrickSetStatusList
from .set_tag_list import BrickSetTagList

logger = logging.getLogger(__name__)


# Individual minifigures list
class IndividualMinifigureList(BrickRecordList[IndividualMinifigure]):
    # Queries
    all_query: str = 'individual_minifigure/list/all'
    damaged_part_query: str = 'individual_minifigure/list/damaged_part'
    instances_by_figure_query: str = 'individual_minifigure/select/instances_by_figure'
    missing_part_query: str = 'individual_minifigure/list/missing_part'
    using_part_query: str = 'individual_minifigure/list/using_part'
    using_storage_query: str = 'individual_minifigure/list/using_storage'
    using_purchase_location_query: str = 'individual_minifigure/list/using_purchase_location'
    without_storage_query: str = 'individual_minifigure/list/without_storage'

    def __init__(self, /):
        super().__init__()

    # Load all individual minifigures
    def all(self, /) -> Self:
        # Prepare context with metadata columns
        context = {
            'owners': BrickSetOwnerList.as_columns() if BrickSetOwnerList.list() else 'NULL AS "no_owners"',
            'statuses': BrickSetStatusList.as_columns(all=True) if BrickSetStatusList.list(all=True) else 'NULL AS "no_statuses"',
            'tags': BrickSetTagList.as_columns() if BrickSetTagList.list() else 'NULL AS "no_tags"',
        }

        self.list(override_query=self.all_query, **context)
        return self

    # Load all individual instances of a specific minifigure figure
    def instances_by_figure(self, figure: str, /) -> Self:
        self.fields.figure = figure

        # Prepare context with metadata columns (using consolidated metadata tables)
        context = {
            'owners': BrickSetOwnerList.as_columns() if BrickSetOwnerList.list() else 'NULL AS "no_owners"',
            'statuses': BrickSetStatusList.as_columns(all=True) if BrickSetStatusList.list(all=True) else 'NULL AS "no_statuses"',
            'tags': BrickSetTagList.as_columns() if BrickSetTagList.list() else 'NULL AS "no_tags"',
        }

        # Load the instances from the database
        self.list(override_query=self.instances_by_figure_query, **context)

        return self

    # Отдельные фигурки, в состав которых входит деталь
    #
    # Наборные фигурки живут в minifigure_list: у них другая таблица
    # деталей, другие колонки и другая карточка, поэтому это отдельный
    # список, а не расширение того.
    def using_part(self, part: str, color: int, /) -> Self:
        return self.by_part(self.using_part_query, part, color)

    # Отдельные фигурки, у которых эта деталь отмечена потерянной
    def missing_part(self, part: str, color: int, /) -> Self:
        return self.by_part(self.missing_part_query, part, color)

    # Отдельные фигурки, у которых эта деталь отмечена повреждённой
    def damaged_part(self, part: str, color: int, /) -> Self:
        return self.by_part(self.damaged_part_query, part, color)

    # Общая часть трёх выборок по детали
    def by_part(self, query: str, part: str, color: int, /) -> Self:
        self.fields.part = part
        self.fields.color = color

        self.list(override_query=query, **self.metadata_columns())

        return self

    # Колонки владельцев, статусов и меток
    #
    # Они динамические: колонка на каждую заведённую метку. Когда их нет
    # вовсе, подставляется заглушка, иначе в списке через запятую
    # окажется пустое место.
    @staticmethod
    def metadata_columns() -> dict[str, str]:
        return {
            'owners': BrickSetOwnerList.as_columns() if BrickSetOwnerList.list() else 'NULL AS "no_owners"',  # noqa: E501
            'statuses': BrickSetStatusList.as_columns(all=True) if BrickSetStatusList.list(all=True) else 'NULL AS "no_statuses"',  # noqa: E501
            'tags': BrickSetTagList.as_columns() if BrickSetTagList.list() else 'NULL AS "no_tags"',  # noqa: E501
        }

    # Load all individual minifigures using a specific storage
    def using_storage(self, storage: 'BrickSetStorage', /) -> Self:
        # Save the storage parameter
        self.fields.storage = storage.fields.id

        # Load the minifigures from the database
        self.list(override_query=self.using_storage_query)

        return self

    # Load all individual minifigures using a specific purchase location
    def using_purchase_location(self, purchase_location: 'BrickSetPurchaseLocation', /) -> Self:
        # Save the purchase location parameter
        self.fields.purchase_location = purchase_location.fields.id

        # Load the minifigures from the database
        self.list(override_query=self.using_purchase_location_query)

        return self

    # Load all individual minifigures without storage
    def without_storage(self, /) -> Self:
        # Load minifigures with no storage
        self.list(override_query=self.without_storage_query)

        return self

    # Base individual minifigure list
    def list(
        self,
        /,
        *,
        override_query: str | None = None,
        order: str | None = None,
        limit: int | None = None,
        **context,
    ) -> None:
        # Load the individual minifigures from the database
        for record in super().select(
            override_query=override_query,
            order=order,
            limit=limit,
            **context
        ):
            individual_minifigure = IndividualMinifigure(record=record)
            self.records.append(individual_minifigure)
