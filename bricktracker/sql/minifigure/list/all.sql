{% extends 'minifigure/base/base.sql' %}

{% block total_missing %}
SUM(IFNULL("problem_join"."total_missing", 0)) AS "total_missing",
{% endblock %}

{% block total_damaged %}
SUM(IFNULL("problem_join"."total_damaged", 0)) AS "total_damaged",
{% endblock %}

{% block total_quantity %}
SUM(IFNULL("combined"."quantity", 0)) AS "total_quantity",
{% endblock %}

{% block total_sets %}
SUM(CASE WHEN "combined"."source_type" = 'set' THEN 1 ELSE 0 END) AS "total_sets",
{% endblock %}

{% block total_individual %}
SUM(CASE WHEN "combined"."source_type" = 'individual' THEN 1 ELSE 0 END) AS "total_individual"
{% endblock %}

{% block join %}
-- LEFT JOIN + SELECT to avoid messing the total
-- Combine parts from both set-based and individual minifigures
LEFT JOIN (
    -- Set-based minifigure parts
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

    UNION ALL

    -- Individual minifigure parts
    SELECT
        "bricktracker_individual_minifigure_parts"."id",
        "combined"."figure",
        SUM("bricktracker_individual_minifigure_parts"."missing") AS "total_missing",
        SUM("bricktracker_individual_minifigure_parts"."damaged") AS "total_damaged"
    FROM "bricktracker_individual_minifigure_parts"
    INNER JOIN "bricktracker_individual_minifigures" ON "bricktracker_individual_minifigure_parts"."id" = "bricktracker_individual_minifigures"."id"
    INNER JOIN "rebrickable_minifigures" AS "combined" ON "bricktracker_individual_minifigures"."figure" = "combined"."figure"
    GROUP BY
        "bricktracker_individual_minifigure_parts"."id",
        "combined"."figure"
) "problem_join"
ON "combined"."id" IS NOT DISTINCT FROM "problem_join"."id"
AND "combined"."figure" IS NOT DISTINCT FROM "problem_join"."figure"
{% endblock %}

{% block where %}
{% if search_query %}
WHERE (LOWER("combined"."name") LIKE LOWER('%{{ search_query }}%'))
{% endif %}
{% endblock %}

{% block group %}
GROUP BY
    "combined"."figure"
{% endblock %}
