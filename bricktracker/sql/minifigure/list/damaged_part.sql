{% extends 'minifigure/base/base.sql' %}

{% block total_damaged %}
SUM("parts_combined"."damaged") AS "total_damaged",
{% endblock %}

{% block join %}
-- Join with parts from both set-based and individual minifigures
LEFT JOIN (
    SELECT
        "bricktracker_parts"."id",
        "bricktracker_parts"."figure",
        "bricktracker_parts"."damaged"
    FROM "bricktracker_parts"

    UNION ALL

    SELECT
        "bricktracker_individual_minifigure_parts"."id",
        "bricktracker_individual_minifigures"."figure",
        "bricktracker_individual_minifigure_parts"."damaged"
    FROM "bricktracker_individual_minifigure_parts"
    INNER JOIN "bricktracker_individual_minifigures"
    ON "bricktracker_individual_minifigure_parts"."id" = "bricktracker_individual_minifigures"."id"
) AS "parts_combined"
ON "combined"."id" IS NOT DISTINCT FROM "parts_combined"."id"
AND "combined"."figure" IS NOT DISTINCT FROM "parts_combined"."figure"
{% endblock %}

{% block where %}
WHERE "combined"."figure" IN (
    -- Find figures with damaged parts from both sources
    SELECT "figure"
    FROM (
        SELECT "bricktracker_parts"."figure"
        FROM "bricktracker_parts"
        WHERE "bricktracker_parts"."part" IS NOT DISTINCT FROM :part
        AND "bricktracker_parts"."color" IS NOT DISTINCT FROM :color
        AND "bricktracker_parts"."figure" IS NOT NULL
        AND "bricktracker_parts"."damaged" > 0

        UNION

        SELECT "bricktracker_individual_minifigures"."figure"
        FROM "bricktracker_individual_minifigure_parts"
        INNER JOIN "bricktracker_individual_minifigures"
        ON "bricktracker_individual_minifigure_parts"."id" = "bricktracker_individual_minifigures"."id"
        WHERE "bricktracker_individual_minifigure_parts"."part" IS NOT DISTINCT FROM :part
        AND "bricktracker_individual_minifigure_parts"."color" IS NOT DISTINCT FROM :color
        AND "bricktracker_individual_minifigure_parts"."damaged" > 0
    ) AS "damaged_figures"
    GROUP BY "figure"
)
{% endblock %}

{% block group %}
GROUP BY
    "combined"."figure"
{% endblock %}
