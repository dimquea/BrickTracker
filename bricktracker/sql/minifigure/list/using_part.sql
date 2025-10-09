{% extends 'minifigure/base/base.sql' %}

{% block total_quantity %}
SUM("combined"."quantity") AS "total_quantity",
{% endblock %}

{% block where %}
WHERE "combined"."figure" IN (
    -- Find figures from both set-based and individual minifigure parts
    SELECT "figure"
    FROM (
        SELECT "bricktracker_parts"."figure"
        FROM "bricktracker_parts"
        WHERE "bricktracker_parts"."part" IS NOT DISTINCT FROM :part
        AND "bricktracker_parts"."color" IS NOT DISTINCT FROM :color
        AND "bricktracker_parts"."figure" IS NOT NULL

        UNION

        SELECT "bricktracker_individual_minifigures"."figure"
        FROM "bricktracker_individual_minifigure_parts"
        INNER JOIN "bricktracker_individual_minifigures"
        ON "bricktracker_individual_minifigure_parts"."id" = "bricktracker_individual_minifigures"."id"
        WHERE "bricktracker_individual_minifigure_parts"."part" IS NOT DISTINCT FROM :part
        AND "bricktracker_individual_minifigure_parts"."color" IS NOT DISTINCT FROM :color
    ) AS "parts_figures"
    GROUP BY "figure"
)
{% endblock %}

{% block group %}
GROUP BY
    "combined"."figure"
{% endblock %}
