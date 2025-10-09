-- Get all individual minifigure instances for a specific figure
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
    "purchase_meta"."name" AS "purchase_location_name"
FROM "bricktracker_individual_minifigures"

INNER JOIN "rebrickable_minifigures"
ON "bricktracker_individual_minifigures"."figure" = "rebrickable_minifigures"."figure"

LEFT JOIN "bricktracker_metadata_storages" AS "storage_meta"
ON "bricktracker_individual_minifigures"."storage" = "storage_meta"."id"

LEFT JOIN "bricktracker_metadata_purchase_locations" AS "purchase_meta"
ON "bricktracker_individual_minifigures"."purchase_location" = "purchase_meta"."id"

WHERE "bricktracker_individual_minifigures"."figure" = :figure

ORDER BY "bricktracker_individual_minifigures"."rowid" DESC
