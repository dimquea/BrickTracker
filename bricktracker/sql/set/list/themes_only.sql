SELECT DISTINCT "rebrickable_sets"."theme_id"
FROM "bricktracker_sets"

INNER JOIN "rebrickable_sets"
ON "bricktracker_sets"."set" IS NOT DISTINCT FROM "rebrickable_sets"."set"

{% block where %}
WHERE 1=1
{% if search_query %}
AND (LOWER("rebrickable_sets"."name") LIKE LOWER('%{{ search_query }}%')
   OR LOWER("rebrickable_sets"."set") LIKE LOWER('%{{ search_query }}%'))
{% endif %}

{% if storage_filter %}
AND EXISTS (
    SELECT 1 FROM "bricktracker_sets" bs_filter
    WHERE bs_filter."set" = "rebrickable_sets"."set"
    AND bs_filter."storage" = '{{ storage_filter }}'
)
{% endif %}

{% if purchase_location_filter %}
AND EXISTS (
    SELECT 1 FROM "bricktracker_sets" bs_filter
    WHERE bs_filter."set" = "rebrickable_sets"."set"
    AND bs_filter."purchase_location" = '{{ purchase_location_filter }}'
)
{% endif %}

{% if status_filter %}
{% if status_filter == 'has-storage' %}
AND EXISTS (
    SELECT 1 FROM "bricktracker_sets" bs_filter
    WHERE bs_filter."set" = "rebrickable_sets"."set"
    AND bs_filter."storage" IS NOT NULL AND bs_filter."storage" != ''
)
{% elif status_filter == '-has-storage' %}
AND NOT EXISTS (
    SELECT 1 FROM "bricktracker_sets" bs_filter
    WHERE bs_filter."set" = "rebrickable_sets"."set"
    AND bs_filter."storage" IS NOT NULL AND bs_filter."storage" != ''
)
{% elif status_filter.startswith('status-') %}
AND EXISTS (
    SELECT 1 FROM "bricktracker_sets" bs_filter
    JOIN "bricktracker_set_statuses" ON bs_filter."id" = "bricktracker_set_statuses"."id"
    WHERE bs_filter."set" = "rebrickable_sets"."set"
    AND "bricktracker_set_statuses"."{{ status_filter.replace('-', '_') }}" = 1
)
{% elif status_filter.startswith('-status-') %}
AND NOT EXISTS (
    SELECT 1 FROM "bricktracker_sets" bs_filter
    JOIN "bricktracker_set_statuses" ON bs_filter."id" = "bricktracker_set_statuses"."id"
    WHERE bs_filter."set" = "rebrickable_sets"."set"
    AND "bricktracker_set_statuses"."{{ status_filter[1:].replace('-', '_') }}" = 1
)
{% elif status_filter == 'has-missing' %}
AND EXISTS (
    SELECT 1 FROM "bricktracker_sets" bs_filter
    JOIN "bricktracker_parts" ON bs_filter."id" = "bricktracker_parts"."id"
    WHERE bs_filter."set" = "rebrickable_sets"."set"
    AND "bricktracker_parts"."missing" > 0
)
{% elif status_filter == '-has-missing' %}
AND NOT EXISTS (
    SELECT 1 FROM "bricktracker_sets" bs_filter
    JOIN "bricktracker_parts" ON bs_filter."id" = "bricktracker_parts"."id"
    WHERE bs_filter."set" = "rebrickable_sets"."set"
    AND "bricktracker_parts"."missing" > 0
)
{% elif status_filter == 'has-damaged' %}
AND EXISTS (
    SELECT 1 FROM "bricktracker_sets" bs_filter
    JOIN "bricktracker_parts" ON bs_filter."id" = "bricktracker_parts"."id"
    WHERE bs_filter."set" = "rebrickable_sets"."set"
    AND "bricktracker_parts"."damaged" > 0
)
{% elif status_filter == '-has-damaged' %}
AND NOT EXISTS (
    SELECT 1 FROM "bricktracker_sets" bs_filter
    JOIN "bricktracker_parts" ON bs_filter."id" = "bricktracker_parts"."id"
    WHERE bs_filter."set" = "rebrickable_sets"."set"
    AND "bricktracker_parts"."damaged" > 0
)
{% elif status_filter == 'has-missing-minifigures' %}
AND EXISTS (
    SELECT 1 FROM "bricktracker_sets" bs_filter
    JOIN "bricktracker_minifigures" ON bs_filter."id" = "bricktracker_minifigures"."id"
    WHERE bs_filter."set" = "rebrickable_sets"."set"
    AND "bricktracker_minifigures"."missing" > 0
)
{% elif status_filter == '-has-missing-minifigures' %}
AND NOT EXISTS (
    SELECT 1 FROM "bricktracker_sets" bs_filter
    JOIN "bricktracker_minifigures" ON bs_filter."id" = "bricktracker_minifigures"."id"
    WHERE bs_filter."set" = "rebrickable_sets"."set"
    AND "bricktracker_minifigures"."missing" > 0
)
{% endif %}
{% endif %}
{% endblock %}