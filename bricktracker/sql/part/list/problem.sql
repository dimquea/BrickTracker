{% extends 'part/base/base.sql' %}

{% block total_missing %}
{% if owner_id and owner_id != 'all' %}
SUM(CASE WHEN "bricktracker_set_owners"."owner_{{ owner_id }}" = 1 THEN "combined"."missing" ELSE 0 END) AS "total_missing",
{% else %}
SUM("combined"."missing") AS "total_missing",
{% endif %}
{% endblock %}

{% block total_damaged %}
{% if owner_id and owner_id != 'all' %}
SUM(CASE WHEN "bricktracker_set_owners"."owner_{{ owner_id }}" = 1 THEN "combined"."damaged" ELSE 0 END) AS "total_damaged",
{% else %}
SUM("combined"."damaged") AS "total_damaged",
{% endif %}
{% endblock %}

{% block total_quantity %}
{% if owner_id and owner_id != 'all' %}
SUM(CASE WHEN "bricktracker_set_owners"."owner_{{ owner_id }}" = 1 THEN "combined"."quantity" * IFNULL("bricktracker_minifigures"."quantity", 1) ELSE 0 END) AS "total_quantity",
{% else %}
SUM("combined"."quantity" * IFNULL("bricktracker_minifigures"."quantity", 1)) AS "total_quantity",
{% endif %}
{% endblock %}

{% block total_sets %}
{% if owner_id and owner_id != 'all' %}
COUNT(DISTINCT CASE WHEN "bricktracker_set_owners"."owner_{{ owner_id }}" = 1 THEN "combined"."id" ELSE NULL END) AS "total_sets",
{% else %}
COUNT(DISTINCT "combined"."id") AS "total_sets",
{% endif %}
{% endblock %}

{% block total_minifigures %}
{% if owner_id and owner_id != 'all' %}
SUM(CASE WHEN "bricktracker_set_owners"."owner_{{ owner_id }}" = 1 THEN IFNULL("bricktracker_minifigures"."quantity", 0) ELSE 0 END) AS "total_minifigures"
{% else %}
SUM(IFNULL("bricktracker_minifigures"."quantity", 0)) AS "total_minifigures"
{% endif %}
{% endblock %}

{% block join %}
-- Join with sets to get owner information
INNER JOIN "bricktracker_sets"
ON "combined"."id" IS NOT DISTINCT FROM "bricktracker_sets"."id"

-- Left join with set owners (using dynamic columns)
LEFT JOIN "bricktracker_set_owners"
ON "bricktracker_sets"."id" IS NOT DISTINCT FROM "bricktracker_set_owners"."id"

-- Left join with minifigures
LEFT JOIN "bricktracker_minifigures"
ON "combined"."id" IS NOT DISTINCT FROM "bricktracker_minifigures"."id"
AND "combined"."figure" IS NOT DISTINCT FROM "bricktracker_minifigures"."figure"
{% endblock %}

{% block where %}
{% set conditions = [] %}
-- Always filter for problematic parts
{% set _ = conditions.append('("combined"."missing" > 0 OR "combined"."damaged" > 0)') %}
{% if owner_id and owner_id != 'all' %}
  {% set _ = conditions.append('"bricktracker_set_owners"."owner_' ~ owner_id ~ '" = 1') %}
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
