-- Get all individual minifigure instances for a specific storage location
SELECT
    "bricktracker_individual_minifigures"."id",
    "bricktracker_individual_minifigures"."figure",
    "bricktracker_individual_minifigures"."quantity",
    "bricktracker_individual_minifigures"."description",
    "bricktracker_individual_minifigures"."storage",
    "bricktracker_individual_minifigures"."purchase_location",
    "rebrickable_minifigures"."number",
    "rebrickable_minifigures"."name",
    "rebrickable_minifigures"."image",
    "rebrickable_minifigures"."number_of_parts",
    "storage_meta"."name" AS "storage_name",
    "purchase_meta"."name" AS "purchase_location_name",
    IFNULL("problem_join"."total_missing", 0) AS "total_missing",
    IFNULL("problem_join"."total_damaged", 0) AS "total_damaged"
FROM "bricktracker_individual_minifigures"

INNER JOIN "rebrickable_minifigures"
ON "bricktracker_individual_minifigures"."figure" = "rebrickable_minifigures"."figure"

LEFT JOIN "bricktracker_metadata_storages" AS "storage_meta"
ON "bricktracker_individual_minifigures"."storage" = "storage_meta"."id"

LEFT JOIN "bricktracker_metadata_purchase_locations" AS "purchase_meta"
ON "bricktracker_individual_minifigures"."purchase_location" = "purchase_meta"."id"

LEFT JOIN (
    SELECT
        "bricktracker_individual_minifigure_parts"."id",
        SUM("bricktracker_individual_minifigure_parts"."missing") AS "total_missing",
        SUM("bricktracker_individual_minifigure_parts"."damaged") AS "total_damaged"
    FROM "bricktracker_individual_minifigure_parts"
    GROUP BY "bricktracker_individual_minifigure_parts"."id"
) "problem_join"
ON "bricktracker_individual_minifigures"."id" = "problem_join"."id"

WHERE "bricktracker_individual_minifigures"."storage" IS NOT DISTINCT FROM :storage

{% if order %}
ORDER BY {{ order }}
{% else %}
ORDER BY "bricktracker_individual_minifigures"."rowid" DESC
{% endif %}

{% if limit %}
LIMIT {{ limit }}
{% endif %}
