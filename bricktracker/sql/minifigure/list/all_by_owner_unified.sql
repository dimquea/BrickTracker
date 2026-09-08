-- Unified query that shows both set minifigures and individual minifigures filtered by owner
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
        {% if owner_id and owner_id != 'all' %}
        CASE WHEN "bricktracker_set_owners"."owner_{{ owner_id }}" = 1 THEN IFNULL("bricktracker_minifigures"."quantity", 0) ELSE 0 END AS "total_quantity",
        CASE WHEN "bricktracker_set_owners"."owner_{{ owner_id }}" = 1 THEN 1 ELSE 0 END AS "total_sets",
        {% else %}
        IFNULL("bricktracker_minifigures"."quantity", 0) AS "total_quantity",
        1 AS "total_sets",
        {% endif %}
        0 AS "total_individual"
    FROM "bricktracker_minifigures"
    INNER JOIN "rebrickable_minifigures"
    ON "bricktracker_minifigures"."figure" IS NOT DISTINCT FROM "rebrickable_minifigures"."figure"
    -- Join with sets to get owner information
    INNER JOIN "bricktracker_sets"
    ON "bricktracker_minifigures"."id" IS NOT DISTINCT FROM "bricktracker_sets"."id"
    -- Join with rebrickable sets for theme/year filtering
    INNER JOIN "rebrickable_sets"
    ON "bricktracker_sets"."set" IS NOT DISTINCT FROM "rebrickable_sets"."set"
    -- Left join with set owners
    LEFT JOIN "bricktracker_set_owners"
    ON "bricktracker_sets"."id" IS NOT DISTINCT FROM "bricktracker_set_owners"."id"
    -- LEFT JOIN for problems
    LEFT JOIN (
        SELECT
            "bricktracker_parts"."id",
            "bricktracker_parts"."figure",
            {% if owner_id and owner_id != 'all' %}
            SUM(CASE WHEN "owner_parts"."owner_{{ owner_id }}" = 1 THEN "bricktracker_parts"."missing" ELSE 0 END) AS "total_missing",
            SUM(CASE WHEN "owner_parts"."owner_{{ owner_id }}" = 1 THEN "bricktracker_parts"."damaged" ELSE 0 END) AS "total_damaged"
            {% else %}
            SUM("bricktracker_parts"."missing") AS "total_missing",
            SUM("bricktracker_parts"."damaged") AS "total_damaged"
            {% endif %}
        FROM "bricktracker_parts"
        INNER JOIN "bricktracker_sets" AS "parts_sets"
        ON "bricktracker_parts"."id" IS NOT DISTINCT FROM "parts_sets"."id"
        LEFT JOIN "bricktracker_set_owners" AS "owner_parts"
        ON "parts_sets"."id" IS NOT DISTINCT FROM "owner_parts"."id"
        WHERE "bricktracker_parts"."figure" IS NOT NULL
        GROUP BY
            "bricktracker_parts"."id",
            "bricktracker_parts"."figure"
    ) "problem_join"
    ON "bricktracker_minifigures"."id" IS NOT DISTINCT FROM "problem_join"."id"
    AND "rebrickable_minifigures"."figure" IS NOT DISTINCT FROM "problem_join"."figure"
    {% set conditions = [] %}
    {# Ни альтернатива, ни counterpart не пополняют коллекцию: первая
       заменяет собой основную фигурку набора, второй собран из уже
       посчитанных деталей. В наборе они видны справкой, в общем списке
       фигурок им делать нечего #}
    {% set _ = conditions.append('"bricktracker_minifigures"."alternate" = 0') %}
    {% set _ = conditions.append('"bricktracker_minifigures"."counterpart" = 0') %}
    {% if owner_id and owner_id != 'all' %}
      {% set _ = conditions.append('"bricktracker_set_owners"."owner_' ~ owner_id ~ '" = 1') %}
    {% endif %}
    {% if theme_id and theme_id != 'all' %}
      {% set _ = conditions.append('"rebrickable_sets"."theme_id" = ' ~ theme_id) %}
    {% endif %}
    {% if year and year != 'all' %}
      {% set _ = conditions.append('"rebrickable_sets"."year" = ' ~ year) %}
    {% endif %}
    {% if search_query %}
      {% set _ = conditions.append('(LOWER("rebrickable_minifigures"."name") LIKE LOWER(\'%' ~ search_query ~ '%\'))') %}
    {% endif %}
    {% if conditions %}
    WHERE {{ conditions | join(' AND ') }}
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
        {% if owner_id and owner_id != 'all' %}
        CASE WHEN "bricktracker_set_owners"."owner_{{ owner_id }}" = 1 THEN IFNULL("bricktracker_individual_minifigures"."quantity", 0) ELSE 0 END AS "total_quantity",
        CASE WHEN "bricktracker_set_owners"."owner_{{ owner_id }}" = 1 THEN 1 ELSE 0 END AS "total_individual",
        {% else %}
        IFNULL("bricktracker_individual_minifigures"."quantity", 0) AS "total_quantity",
        1 AS "total_individual",
        {% endif %}
        0 AS "total_sets"
    FROM "bricktracker_individual_minifigures"
    INNER JOIN "rebrickable_minifigures"
    ON "bricktracker_individual_minifigures"."figure" IS NOT DISTINCT FROM "rebrickable_minifigures"."figure"
    -- Join with set owners for individual minifigures
    LEFT JOIN "bricktracker_set_owners"
    ON "bricktracker_individual_minifigures"."id" IS NOT DISTINCT FROM "bricktracker_set_owners"."id"
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
    {% set ind_conditions = [] %}
    {% if owner_id and owner_id != 'all' %}
      {% set _ = ind_conditions.append('"bricktracker_set_owners"."owner_' ~ owner_id ~ '" = 1') %}
    {% endif %}
    {% if search_query %}
      {% set _ = ind_conditions.append('(LOWER("rebrickable_minifigures"."name") LIKE LOWER(\'%' ~ search_query ~ '%\'))') %}
    {% endif %}
    {% if ind_conditions %}
    WHERE {{ ind_conditions | join(' AND ') }}
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
