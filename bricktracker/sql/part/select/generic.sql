{% extends 'part/base/base.sql' %}

{% block total_missing %}
SUM("combined"."missing") AS "total_missing",
{% endblock %}

{% block total_damaged %}
SUM("combined"."damaged") AS "total_damaged",
{% endblock %}

{% block total_quantity %}
SUM((NOT "combined"."spare") * "combined"."quantity" * IFNULL("minifigure_quantities"."quantity", 1)) AS "total_quantity",
{% endblock %}

{% block total_spare %}
SUM("combined"."spare" * "combined"."quantity" * IFNULL("minifigure_quantities"."quantity", 1)) AS "total_spare",
{% endblock %}

{% block join %}
-- Join to get minifigure quantities from both set-based and individual minifigures
LEFT JOIN (
    -- Set-based minifigure quantities
    SELECT
        "bricktracker_minifigures"."id",
        "bricktracker_minifigures"."figure",
        "bricktracker_minifigures"."quantity"
    FROM "bricktracker_minifigures"

    UNION ALL

    -- Individual minifigure quantities
    SELECT
        "bricktracker_individual_minifigures"."id",
        "bricktracker_individual_minifigures"."figure",
        "bricktracker_individual_minifigures"."quantity"
    FROM "bricktracker_individual_minifigures"
) AS "minifigure_quantities"
ON "combined"."id" IS NOT DISTINCT FROM "minifigure_quantities"."id"
AND "combined"."figure" IS NOT DISTINCT FROM "minifigure_quantities"."figure"
{% endblock %}

{% block where %}
WHERE "combined"."part" IS NOT DISTINCT FROM :part
AND "combined"."color" IS NOT DISTINCT FROM :color
{% endblock %}

{% block group %}
GROUP BY
    "combined"."part",
    "combined"."color"
{% endblock %}
