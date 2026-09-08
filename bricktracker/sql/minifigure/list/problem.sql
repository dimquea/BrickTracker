-- Фигурки, у которых есть отметки missing или damaged
--
-- Запрос отдельный, а не наследник minifigure/base/base.sql, потому что
-- странице проблем нужен набор: отметка живёт на паре набор-фигурка, и
-- без набора непонятно, где именно фигурки не хватает. Ровно поэтому же
-- строка здесь одна на пару, а не одна на фигурку, как в остальных
-- списках.
--
-- Альтернативы не исключаем: если пользователь отметил такую, ему это
-- зачем-то понадобилось, и прятать отметку было бы хуже, чем показать.
SELECT
    "bricktracker_minifigures"."id",
    "bricktracker_minifigures"."quantity",
    "bricktracker_minifigures"."missing",
    "bricktracker_minifigures"."damaged",
    "bricktracker_minifigures"."alternate",
    "bricktracker_minifigures"."match_id",
    "rebrickable_minifigures"."figure",
    "rebrickable_minifigures"."number",
    "rebrickable_minifigures"."number_of_parts",
    "rebrickable_minifigures"."name",
    "rebrickable_minifigures"."image",
    "bricktracker_sets"."set",
    "rebrickable_sets"."name" AS "set_name"

FROM "bricktracker_minifigures"

INNER JOIN "rebrickable_minifigures"
ON "bricktracker_minifigures"."figure" IS NOT DISTINCT FROM "rebrickable_minifigures"."figure"

INNER JOIN "bricktracker_sets"
ON "bricktracker_minifigures"."id" IS NOT DISTINCT FROM "bricktracker_sets"."id"

INNER JOIN "rebrickable_sets"
ON "bricktracker_sets"."set" IS NOT DISTINCT FROM "rebrickable_sets"."set"

WHERE "bricktracker_minifigures"."missing" > 0
OR "bricktracker_minifigures"."damaged" > 0

{% if order %}
ORDER BY {{ order }}
{% endif %}
