{% extends 'set/metadata/storage/base.sql' %}

{% block total_sets %}
IFNULL(COUNT(DISTINCT "bricktracker_sets"."id"), 0) AS "total_sets",
IFNULL(COUNT(DISTINCT "bricktracker_individual_minifigures"."id"), 0) AS "total_individual_minifigures",
IFNULL(COUNT(DISTINCT "bricktracker_individual_parts"."id"), 0) AS "total_individual_parts"
{% endblock %}

{% block join %}
LEFT JOIN "bricktracker_sets"
ON "bricktracker_metadata_storages"."id" IS NOT DISTINCT FROM "bricktracker_sets"."storage"

LEFT JOIN "bricktracker_individual_minifigures"
ON "bricktracker_metadata_storages"."id" IS NOT DISTINCT FROM "bricktracker_individual_minifigures"."storage"

LEFT JOIN "bricktracker_individual_parts"
ON "bricktracker_metadata_storages"."id" IS NOT DISTINCT FROM "bricktracker_individual_parts"."storage"
{% endblock %}

{% block group %}
GROUP BY "bricktracker_metadata_storages"."id"
{% endblock %}