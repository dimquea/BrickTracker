{% extends 'minifigure/base/base.sql' %}

{% block total_missing %}
SUM(IFNULL("problem_join"."total_missing", 0)) AS "total_missing",
{% endblock %}

{% block total_damaged %}
SUM(IFNULL("problem_join"."total_damaged", 0)) AS "total_damaged",
{% endblock %}

{% block total_quantity %}
{% if owner_id and owner_id != 'all' %}
SUM(CASE
    WHEN "combined"."source_type" = 'set' AND "set_owners"."owner_{{ owner_id }}" = 1 THEN IFNULL("combined"."quantity", 0)
    WHEN "combined"."source_type" = 'individual' AND "individual_owners"."owner_{{ owner_id }}" = 1 THEN IFNULL("combined"."quantity", 0)
    ELSE 0
END) AS "total_quantity",
{% else %}
SUM(IFNULL("combined"."quantity", 0)) AS "total_quantity",
{% endif %}
{% endblock %}

{% block total_sets %}
{% if owner_id and owner_id != 'all' %}
SUM(CASE
    WHEN "combined"."source_type" = 'set' AND "set_owners"."owner_{{ owner_id }}" = 1 THEN 1
    ELSE 0
END) AS "total_sets",
{% else %}
SUM(CASE WHEN "combined"."source_type" = 'set' THEN 1 ELSE 0 END) AS "total_sets",
{% endif %}
{% endblock %}

{% block total_individual %}
{% if owner_id and owner_id != 'all' %}
SUM(CASE
    WHEN "combined"."source_type" = 'individual' AND "individual_owners"."owner_{{ owner_id }}" = 1 THEN 1
    ELSE 0
END) AS "total_individual"
{% else %}
SUM(CASE WHEN "combined"."source_type" = 'individual' THEN 1 ELSE 0 END) AS "total_individual"
{% endif %}
{% endblock %}

{% block join %}
-- Join with set owners for set-based minifigures
LEFT JOIN "bricktracker_sets"
ON "combined"."id" = "bricktracker_sets"."id" AND "combined"."source_type" = 'set'

LEFT JOIN "bricktracker_set_owners" AS "set_owners"
ON "bricktracker_sets"."id" = "set_owners"."id"

-- Join with individual minifigure owners for individual minifigures
LEFT JOIN "bricktracker_individual_minifigure_owners" AS "individual_owners"
ON "combined"."id" = "individual_owners"."id" AND "combined"."source_type" = 'individual'

-- LEFT JOIN + SELECT to avoid messing the total
LEFT JOIN (
    -- Set-based minifigure parts
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
    ON "bricktracker_parts"."id" = "parts_sets"."id"
    LEFT JOIN "bricktracker_set_owners" AS "owner_parts"
    ON "parts_sets"."id" = "owner_parts"."id"
    WHERE "bricktracker_parts"."figure" IS NOT NULL
    GROUP BY
        "bricktracker_parts"."id",
        "bricktracker_parts"."figure"

    UNION ALL

    -- Individual minifigure parts
    SELECT
        "bricktracker_individual_minifigure_parts"."id",
        "bricktracker_individual_minifigures"."figure",
        {% if owner_id and owner_id != 'all' %}
        SUM(CASE WHEN "owner_individual"."owner_{{ owner_id }}" = 1 THEN "bricktracker_individual_minifigure_parts"."missing" ELSE 0 END) AS "total_missing",
        SUM(CASE WHEN "owner_individual"."owner_{{ owner_id }}" = 1 THEN "bricktracker_individual_minifigure_parts"."damaged" ELSE 0 END) AS "total_damaged"
        {% else %}
        SUM("bricktracker_individual_minifigure_parts"."missing") AS "total_missing",
        SUM("bricktracker_individual_minifigure_parts"."damaged") AS "total_damaged"
        {% endif %}
    FROM "bricktracker_individual_minifigure_parts"
    INNER JOIN "bricktracker_individual_minifigures"
    ON "bricktracker_individual_minifigure_parts"."id" = "bricktracker_individual_minifigures"."id"
    LEFT JOIN "bricktracker_individual_minifigure_owners" AS "owner_individual"
    ON "bricktracker_individual_minifigures"."id" = "owner_individual"."id"
    GROUP BY
        "bricktracker_individual_minifigure_parts"."id",
        "bricktracker_individual_minifigures"."figure"
) "problem_join"
ON "combined"."id" = "problem_join"."id"
AND "combined"."figure" = "problem_join"."figure"
{% endblock %}

{% block where %}
{% set conditions = [] %}
{% if owner_id and owner_id != 'all' %}
  {% set _ = conditions.append('(("combined"."source_type" = \'set\' AND "set_owners"."owner_' ~ owner_id ~ '" = 1) OR ("combined"."source_type" = \'individual\' AND "individual_owners"."owner_' ~ owner_id ~ '" = 1))') %}
{% endif %}
{% if search_query %}
  {% set _ = conditions.append('(LOWER("combined"."name") LIKE LOWER(\'%' ~ search_query ~ '%\'))') %}
{% endif %}
{% if conditions %}
WHERE {{ conditions | join(' AND ') }}
{% endif %}
{% endblock %}

{% block group %}
GROUP BY
    "combined"."figure"
{% endblock %}