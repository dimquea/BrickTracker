{% extends 'set/metadata/storage/base.sql' %}

{% block total_sets %}
IFNULL(COUNT(DISTINCT "bricktracker_sets"."id"), 0) AS "total_sets",
IFNULL(COUNT(DISTINCT "bricktracker_individual_minifigures"."id"), 0) AS "total_individual_minifigures"
{% endblock %}

{% block join %}
LEFT JOIN "bricktracker_sets"
ON "bricktracker_metadata_storages"."id" IS NOT DISTINCT FROM "bricktracker_sets"."storage"

LEFT JOIN "bricktracker_individual_minifigures"
ON "bricktracker_metadata_storages"."id" IS NOT DISTINCT FROM "bricktracker_individual_minifigures"."storage"
{% endblock %}

{% block group %}
GROUP BY "bricktracker_metadata_storages"."id"
{% endblock %}