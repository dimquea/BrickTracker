-- Отдельные фигурки, в состав которых входит деталь
--
-- Детали наборных фигурок лежат в bricktracker_parts, детали отдельных —
-- в своей таблице, и запросы страницы детали смотрели только в первую.
-- Поэтому фигурка, заведённая отдельно, на странице своей же детали не
-- показывалась вовсе.
--
-- Форма запроса повторяет individual_minifigure/select/instances_by_figure:
-- карточка отдельной фигурки одна и та же, и ей нужны те же колонки.
SELECT
    "bricktracker_individual_minifigures"."id",
    "bricktracker_individual_minifigures"."figure",
    "bricktracker_individual_minifigures"."quantity",
    "bricktracker_individual_minifigures"."description",
    "bricktracker_individual_minifigures"."storage",
    "bricktracker_individual_minifigures"."purchase_location",
    "bricktracker_individual_minifigures"."purchase_date",
    "bricktracker_individual_minifigures"."purchase_price",
    "rebrickable_minifigures"."number",
    "rebrickable_minifigures"."name",
    "rebrickable_minifigures"."image",
    "rebrickable_minifigures"."number_of_parts",
    "storage_meta"."name" AS "storage_name",
    "purchase_meta"."name" AS "purchase_location_name",
    {{ owners }},
    {{ statuses }},
    {{ tags }},
    IFNULL("problem_join"."total_missing", 0) AS "total_missing",
    IFNULL("problem_join"."total_damaged", 0) AS "total_damaged"
FROM "bricktracker_individual_minifigures"

INNER JOIN "rebrickable_minifigures"
ON "bricktracker_individual_minifigures"."figure" = "rebrickable_minifigures"."figure"

LEFT JOIN "bricktracker_metadata_storages" AS "storage_meta"
ON "bricktracker_individual_minifigures"."storage" = "storage_meta"."id"

LEFT JOIN "bricktracker_metadata_purchase_locations" AS "purchase_meta"
ON "bricktracker_individual_minifigures"."purchase_location" = "purchase_meta"."id"

LEFT JOIN "bricktracker_set_owners"
ON "bricktracker_individual_minifigures"."id" = "bricktracker_set_owners"."id"

LEFT JOIN "bricktracker_set_statuses"
ON "bricktracker_individual_minifigures"."id" = "bricktracker_set_statuses"."id"

LEFT JOIN "bricktracker_set_tags"
ON "bricktracker_individual_minifigures"."id" = "bricktracker_set_tags"."id"

LEFT JOIN (
    SELECT
        "bricktracker_individual_minifigure_parts"."id",
        SUM("bricktracker_individual_minifigure_parts"."missing") AS "total_missing",
        SUM("bricktracker_individual_minifigure_parts"."damaged") AS "total_damaged"
    FROM "bricktracker_individual_minifigure_parts"
    GROUP BY "bricktracker_individual_minifigure_parts"."id"
) "problem_join"
ON "bricktracker_individual_minifigures"."id" = "problem_join"."id"

WHERE EXISTS (
    SELECT 1
    FROM "bricktracker_individual_minifigure_parts"
    WHERE "bricktracker_individual_minifigure_parts"."id" IS NOT DISTINCT FROM "bricktracker_individual_minifigures"."id"
    AND "bricktracker_individual_minifigure_parts"."part" IS NOT DISTINCT FROM :part
    AND "bricktracker_individual_minifigure_parts"."color" IS NOT DISTINCT FROM :color
    {% block condition %}{% endblock %}
)

ORDER BY "bricktracker_individual_minifigures"."rowid" DESC
