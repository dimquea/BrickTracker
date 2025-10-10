{% extends 'part/base/base.sql' %}

{% block total_missing %}
{% if owner_id and owner_id != 'all' %}
SUM(CASE
    WHEN "combined"."source_type" = 'set' AND "bricktracker_set_owners"."owner_{{ owner_id }}" = 1 THEN "combined"."missing"
    WHEN "combined"."source_type" = 'individual' AND "bricktracker_individual_minifigure_owners"."owner_{{ owner_id }}" = 1 THEN "combined"."missing"
    ELSE 0
END) AS "total_missing",
{% else %}
SUM("combined"."missing") AS "total_missing",
{% endif %}
{% endblock %}

{% block total_damaged %}
{% if owner_id and owner_id != 'all' %}
SUM(CASE
    WHEN "combined"."source_type" = 'set' AND "bricktracker_set_owners"."owner_{{ owner_id }}" = 1 THEN "combined"."damaged"
    WHEN "combined"."source_type" = 'individual' AND "bricktracker_individual_minifigure_owners"."owner_{{ owner_id }}" = 1 THEN "combined"."damaged"
    ELSE 0
END) AS "total_damaged",
{% else %}
SUM("combined"."damaged") AS "total_damaged",
{% endif %}
{% endblock %}

{% block total_quantity %}
{% if owner_id and owner_id != 'all' %}
SUM(CASE
    WHEN "combined"."source_type" = 'set' AND "bricktracker_set_owners"."owner_{{ owner_id }}" = 1 THEN "combined"."quantity" * IFNULL("bricktracker_minifigures"."quantity", 1)
    WHEN "combined"."source_type" = 'individual' AND "bricktracker_individual_minifigure_owners"."owner_{{ owner_id }}" = 1 THEN "combined"."quantity" * IFNULL("bricktracker_individual_minifigures"."quantity", 1)
    ELSE 0
END) AS "total_quantity",
{% else %}
SUM(CASE
    WHEN "combined"."source_type" = 'set' THEN "combined"."quantity" * IFNULL("bricktracker_minifigures"."quantity", 1)
    WHEN "combined"."source_type" = 'individual' THEN "combined"."quantity" * IFNULL("bricktracker_individual_minifigures"."quantity", 1)
    ELSE "combined"."quantity"
END) AS "total_quantity",
{% endif %}
{% endblock %}

{% block total_sets %}
{% if owner_id and owner_id != 'all' %}
COUNT(DISTINCT CASE
    WHEN "combined"."source_type" = 'set' AND "bricktracker_set_owners"."owner_{{ owner_id }}" = 1 THEN "combined"."id"
    ELSE NULL
END) AS "total_sets",
{% else %}
COUNT(DISTINCT CASE WHEN "combined"."source_type" = 'set' THEN "combined"."id" ELSE NULL END) AS "total_sets",
{% endif %}
{% endblock %}

{% block total_minifigures %}
{% if owner_id and owner_id != 'all' %}
SUM(CASE
    WHEN "combined"."source_type" = 'set' AND "bricktracker_set_owners"."owner_{{ owner_id }}" = 1 THEN IFNULL("bricktracker_minifigures"."quantity", 0)
    WHEN "combined"."source_type" = 'individual' AND "bricktracker_individual_minifigure_owners"."owner_{{ owner_id }}" = 1 THEN IFNULL("bricktracker_individual_minifigures"."quantity", 0)
    ELSE 0
END) AS "total_minifigures"
{% else %}
SUM(CASE
    WHEN "combined"."source_type" = 'set' THEN IFNULL("bricktracker_minifigures"."quantity", 0)
    WHEN "combined"."source_type" = 'individual' THEN IFNULL("bricktracker_individual_minifigures"."quantity", 0)
    ELSE 0
END) AS "total_minifigures"
{% endif %}
{% endblock %}

{% block join %}
-- Left join with sets for set-based parts
LEFT JOIN "bricktracker_sets"
ON "combined"."source_type" = 'set'
AND "combined"."id" IS NOT DISTINCT FROM "bricktracker_sets"."id"

-- Left join with set owners (using dynamic columns)
LEFT JOIN "bricktracker_set_owners"
ON "bricktracker_sets"."id" IS NOT DISTINCT FROM "bricktracker_set_owners"."id"

-- Left join with set-based minifigures
LEFT JOIN "bricktracker_minifigures"
ON "combined"."source_type" = 'set'
AND "combined"."id" IS NOT DISTINCT FROM "bricktracker_minifigures"."id"
AND "combined"."figure" IS NOT DISTINCT FROM "bricktracker_minifigures"."figure"

-- Left join with individual minifigures
LEFT JOIN "bricktracker_individual_minifigures"
ON "combined"."source_type" = 'individual'
AND "combined"."id" IS NOT DISTINCT FROM "bricktracker_individual_minifigures"."id"

-- Left join with individual minifigure owners
LEFT JOIN "bricktracker_individual_minifigure_owners"
ON "bricktracker_individual_minifigures"."id" IS NOT DISTINCT FROM "bricktracker_individual_minifigure_owners"."id"
{% endblock %}

{% block where %}
{% set conditions = [] %}
-- Always filter for problematic parts
{% set _ = conditions.append('("combined"."missing" > 0 OR "combined"."damaged" > 0)') %}
{% if owner_id and owner_id != 'all' %}
  {% set owner_condition = '(("combined"."source_type" = \'set\' AND "bricktracker_set_owners"."owner_' ~ owner_id ~ '" = 1) OR ("combined"."source_type" = \'individual\' AND "bricktracker_individual_minifigure_owners"."owner_' ~ owner_id ~ '" = 1))' %}
  {% set _ = conditions.append(owner_condition) %}
{% endif %}
{% if color_id and color_id != 'all' %}
  {% set _ = conditions.append('"combined"."color" = ' ~ color_id) %}
{% endif %}
{% if search_query %}
  {% set search_condition = '(LOWER("rebrickable_parts"."name") LIKE LOWER(\'%' ~ search_query ~ '%\') OR LOWER("rebrickable_parts"."color_name") LIKE LOWER(\'%' ~ search_query ~ '%\') OR LOWER("combined"."part") LIKE LOWER(\'%' ~ search_query ~ '%\'))' %}
  {% set _ = conditions.append(search_condition) %}
{% endif %}
{% if skip_spare_parts %}
  {% set _ = conditions.append('"combined"."spare" = 0') %}
{% endif %}
WHERE {{ conditions | join(' AND ') }}
{% endblock %}

{% block group %}
GROUP BY
    "combined"."part",
    "combined"."color",
    "combined"."spare"
{% endblock %}
