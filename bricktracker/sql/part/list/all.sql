{% extends 'part/base/base.sql' %}

{% block total_missing %}
SUM("combined"."missing") AS "total_missing",
{% endblock %}

{% block total_damaged %}
SUM("combined"."damaged") AS "total_damaged",
{% endblock %}

{% block total_quantity %}
SUM("combined"."counted" * IFNULL("minifigure_quantities"."quantity", 1)) AS "total_quantity",
{% endblock %}

{% block total_sets %}
IFNULL(COUNT(DISTINCT CASE WHEN "combined"."source_type" = 'set' THEN "combined"."id" ELSE NULL END), 0) AS "total_sets",
{% endblock %}

{% block total_minifigures %}
SUM(IFNULL("minifigure_quantities"."quantity", 0)) AS "total_minifigures"
{% endblock %}

{% block join %}
-- Join to get minifigure quantities from both set-based and individual minifigures
LEFT JOIN (
    SELECT
        "bricktracker_minifigures"."id",
        "bricktracker_minifigures"."figure",
        -- Альтернатива и counterpart не пополняют коллекцию
        CASE WHEN "bricktracker_minifigures"."alternate" = 0
              AND "bricktracker_minifigures"."counterpart" = 0
             THEN "bricktracker_minifigures"."quantity"
             ELSE 0 END AS "quantity"
    FROM "bricktracker_minifigures"

    UNION ALL

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
{% set conditions = [] %}
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
{% if individuals_filter %}
  {% set _ = conditions.append('"combined"."source_type" = \'individual_part\'') %}
{% endif %}
{% if conditions %}
WHERE {{ conditions | join(' AND ') }}
{% endif %}
{% endblock %}

{% block group %}
GROUP BY
    "combined"."part",
    "combined"."color",
    "combined"."spare"
{% endblock %}
