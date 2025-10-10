-- Get a specific individual minifigure instance by ID
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
    "purchase_meta"."name" AS "purchase_location_name"{{ owners }}{{ statuses }}{{ tags }}
FROM "bricktracker_individual_minifigures"

INNER JOIN "rebrickable_minifigures"
ON "bricktracker_individual_minifigures"."figure" = "rebrickable_minifigures"."figure"

LEFT JOIN "bricktracker_metadata_storages" AS "storage_meta"
ON "bricktracker_individual_minifigures"."storage" = "storage_meta"."id"

LEFT JOIN "bricktracker_metadata_purchase_locations" AS "purchase_meta"
ON "bricktracker_individual_minifigures"."purchase_location" = "purchase_meta"."id"

LEFT JOIN "bricktracker_individual_minifigure_owners"
ON "bricktracker_individual_minifigures"."id" IS NOT DISTINCT FROM "bricktracker_individual_minifigure_owners"."id"

LEFT JOIN "bricktracker_individual_minifigure_statuses"
ON "bricktracker_individual_minifigures"."id" IS NOT DISTINCT FROM "bricktracker_individual_minifigure_statuses"."id"

LEFT JOIN "bricktracker_individual_minifigure_tags"
ON "bricktracker_individual_minifigures"."id" IS NOT DISTINCT FROM "bricktracker_individual_minifigure_tags"."id"

WHERE "bricktracker_individual_minifigures"."id" = :id
