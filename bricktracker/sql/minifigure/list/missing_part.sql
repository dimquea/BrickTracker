{% extends 'minifigure/base/base.sql' %}

{% block total_missing %}
SUM("parts_combined"."missing") AS "total_missing",
{% endblock %}

{% block join %}
-- Join with parts from both set-based and individual minifigures
LEFT JOIN (
    SELECT
        "bricktracker_parts"."id",
        "bricktracker_parts"."figure",
        "bricktracker_parts"."missing"
    FROM "bricktracker_parts"

    UNION ALL

    SELECT
        "bricktracker_individual_minifigure_parts"."id",
        "bricktracker_individual_minifigures"."figure",
        "bricktracker_individual_minifigure_parts"."missing"
    FROM "bricktracker_individual_minifigure_parts"
    INNER JOIN "bricktracker_individual_minifigures"
    ON "bricktracker_individual_minifigure_parts"."id" = "bricktracker_individual_minifigures"."id"
) AS "parts_combined"
ON "combined"."id" IS NOT DISTINCT FROM "parts_combined"."id"
AND "combined"."figure" IS NOT DISTINCT FROM "parts_combined"."figure"
{% endblock %}

{% block where %}
WHERE "combined"."figure" IN (
    -- Find figures with missing parts from both sources
    SELECT "figure"
    FROM (
        SELECT "bricktracker_parts"."figure"
        FROM "bricktracker_parts"
        WHERE "bricktracker_parts"."part" IS NOT DISTINCT FROM :part
        AND "bricktracker_parts"."color" IS NOT DISTINCT FROM :color
        AND "bricktracker_parts"."figure" IS NOT NULL
        AND "bricktracker_parts"."missing" > 0

        UNION

        SELECT "bricktracker_individual_minifigures"."figure"
        FROM "bricktracker_individual_minifigure_parts"
        INNER JOIN "bricktracker_individual_minifigures"
        ON "bricktracker_individual_minifigure_parts"."id" = "bricktracker_individual_minifigures"."id"
        WHERE "bricktracker_individual_minifigure_parts"."part" IS NOT DISTINCT FROM :part
        AND "bricktracker_individual_minifigure_parts"."color" IS NOT DISTINCT FROM :color
        AND "bricktracker_individual_minifigure_parts"."missing" > 0
    ) AS "missing_figures"
    GROUP BY "figure"
)
{% endblock %}

{% block group %}
GROUP BY
    "combined"."figure"
{% endblock %}
