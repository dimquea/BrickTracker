-- Unified query that shows both set minifigures and individual minifigures
SELECT
    "figure",
    "number",
    "number_of_parts",
    "name",
    "image",
    SUM("quantity") AS "quantity",
    SUM("total_missing") AS "total_missing",
    SUM("total_damaged") AS "total_damaged",
    SUM("total_quantity") AS "total_quantity",
    SUM("total_sets") AS "total_sets"
FROM (
    -- Set minifigures
    SELECT
        "rebrickable_minifigures"."figure",
        "rebrickable_minifigures"."number",
        "rebrickable_minifigures"."number_of_parts",
        "rebrickable_minifigures"."name",
        "rebrickable_minifigures"."image",
        "bricktracker_minifigures"."quantity",
        IFNULL("problem_join"."total_missing", 0) AS "total_missing",
        IFNULL("problem_join"."total_damaged", 0) AS "total_damaged",
        IFNULL("bricktracker_minifigures"."quantity", 0) AS "total_quantity",
        1 AS "total_sets",
        0 AS "total_individual"
    FROM "bricktracker_minifigures"
    INNER JOIN "rebrickable_minifigures"
    ON "bricktracker_minifigures"."figure" IS NOT DISTINCT FROM "rebrickable_minifigures"."figure"
    {% if theme_id or year %}
    -- Join with sets for theme/year filtering
    INNER JOIN "bricktracker_sets" AS "filter_sets"
    ON "bricktracker_minifigures"."id" IS NOT DISTINCT FROM "filter_sets"."id"
    INNER JOIN "rebrickable_sets" AS "filter_rs"
    ON "filter_sets"."set" IS NOT DISTINCT FROM "filter_rs"."set"
    {% endif %}
    -- LEFT JOIN for problems
    LEFT JOIN (
        SELECT
            "bricktracker_parts"."id",
            "bricktracker_parts"."figure",
            SUM("bricktracker_parts"."missing") AS "total_missing",
            SUM("bricktracker_parts"."damaged") AS "total_damaged"
        FROM "bricktracker_parts"
        WHERE "bricktracker_parts"."figure" IS NOT NULL
        GROUP BY
            "bricktracker_parts"."id",
            "bricktracker_parts"."figure"
    ) "problem_join"
    ON "bricktracker_minifigures"."id" IS NOT DISTINCT FROM "problem_join"."id"
    AND "rebrickable_minifigures"."figure" IS NOT DISTINCT FROM "problem_join"."figure"
    WHERE 1=1
    -- Ни альтернатива, ни counterpart не пополняют коллекцию: первая
    -- заменяет собой основную фигурку набора, второй собран из уже
    -- посчитанных деталей. В наборе они видны справкой, в общем списке
    -- фигурок им делать нечего
    AND "bricktracker_minifigures"."alternate" = 0
    AND "bricktracker_minifigures"."counterpart" = 0
    {% if theme_id and theme_id != 'all' %}
    AND "filter_rs"."theme_id" = {{ theme_id }}
    {% endif %}
    {% if year and year != 'all' %}
    AND "filter_rs"."year" = {{ year }}
    {% endif %}
    {% if search_query %}
    AND (LOWER("rebrickable_minifigures"."name") LIKE LOWER('%{{ search_query }}%'))
    {% endif %}

    UNION ALL

    -- Individual minifigures
    SELECT
        "rebrickable_minifigures"."figure",
        "rebrickable_minifigures"."number",
        "rebrickable_minifigures"."number_of_parts",
        "rebrickable_minifigures"."name",
        "rebrickable_minifigures"."image",
        "bricktracker_individual_minifigures"."quantity",
        IFNULL("ind_problem_join"."total_missing", 0) AS "total_missing",
        IFNULL("ind_problem_join"."total_damaged", 0) AS "total_damaged",
        IFNULL("bricktracker_individual_minifigures"."quantity", 0) AS "total_quantity",
        0 AS "total_sets",
        1 AS "total_individual"
    FROM "bricktracker_individual_minifigures"
    INNER JOIN "rebrickable_minifigures"
    ON "bricktracker_individual_minifigures"."figure" IS NOT DISTINCT FROM "rebrickable_minifigures"."figure"
    -- LEFT JOIN for individual minifigure problems
    LEFT JOIN (
        SELECT
            "bricktracker_individual_minifigure_parts"."id",
            SUM("bricktracker_individual_minifigure_parts"."missing") AS "total_missing",
            SUM("bricktracker_individual_minifigure_parts"."damaged") AS "total_damaged"
        FROM "bricktracker_individual_minifigure_parts"
        GROUP BY "bricktracker_individual_minifigure_parts"."id"
    ) "ind_problem_join"
    ON "bricktracker_individual_minifigures"."id" IS NOT DISTINCT FROM "ind_problem_join"."id"
    WHERE 1=1
    {% if search_query %}
    AND (LOWER("rebrickable_minifigures"."name") LIKE LOWER('%{{ search_query }}%'))
    {% endif %}
) "combined"
GROUP BY
    "figure",
    "number",
    "number_of_parts",
    "name",
    "image"
{% if problems_filter or individuals_filter %}
HAVING 1=1
{% if problems_filter == 'missing' %}
AND SUM("total_missing") > 0
{% elif problems_filter == 'damaged' %}
AND SUM("total_damaged") > 0
{% elif problems_filter == 'both' %}
AND SUM("total_missing") > 0 AND SUM("total_damaged") > 0
{% endif %}
{% if individuals_filter == 'only' %}
AND SUM("total_individual") > 0
{% elif individuals_filter == 'exclude' %}
AND SUM("total_sets") > 0
{% endif %}
{% endif %}

{% if order %}
ORDER BY {{ order.replace('"rebrickable_minifigures"."', '"') }}
{% endif %}

{% if limit %}
LIMIT {{ limit }}
{% endif %}

{% if offset %}
OFFSET {{ offset }}
{% endif %}
