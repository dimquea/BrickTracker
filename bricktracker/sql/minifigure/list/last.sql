{% extends 'minifigure/base/base.sql' %}

{% block total_missing %}
SUM("parts_combined"."missing") AS "total_missing",
{% endblock %}

{% block total_damaged %}
SUM("parts_combined"."damaged") AS "total_damaged",
{% endblock %}

{% block join %}
-- Join with parts from both set-based and individual minifigures
LEFT JOIN (
    SELECT
        "bricktracker_parts"."id",
        "bricktracker_parts"."figure",
        "bricktracker_parts"."missing",
        "bricktracker_parts"."damaged"
    FROM "bricktracker_parts"

    UNION ALL

    SELECT
        "bricktracker_individual_minifigure_parts"."id",
        "bricktracker_individual_minifigures"."figure",
        "bricktracker_individual_minifigure_parts"."missing",
        "bricktracker_individual_minifigure_parts"."damaged"
    FROM "bricktracker_individual_minifigure_parts"
    INNER JOIN "bricktracker_individual_minifigures"
    ON "bricktracker_individual_minifigure_parts"."id" = "bricktracker_individual_minifigures"."id"
) AS "parts_combined"
ON "combined"."id" IS NOT DISTINCT FROM "parts_combined"."id"
AND "combined"."figure" IS NOT DISTINCT FROM "parts_combined"."figure"
{% endblock %}

{% block group %}
GROUP BY
    "combined"."figure",
    "combined"."id"
{% endblock %}
