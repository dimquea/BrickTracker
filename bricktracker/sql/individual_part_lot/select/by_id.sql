SELECT
    "bricktracker_individual_part_lots"."id",
    "bricktracker_individual_part_lots"."name",
    "bricktracker_individual_part_lots"."description",
    "bricktracker_individual_part_lots"."created_date",
    "bricktracker_individual_part_lots"."storage",
    "bricktracker_individual_part_lots"."purchase_location",
    "bricktracker_individual_part_lots"."purchase_date",
    "bricktracker_individual_part_lots"."purchase_price",
    "bricktracker_metadata_storages"."name" AS "storage_name",
    "bricktracker_metadata_purchase_locations"."name" AS "purchase_location_name"
FROM "bricktracker_individual_part_lots"
LEFT JOIN "bricktracker_metadata_storages"
    ON "bricktracker_individual_part_lots"."storage" IS NOT DISTINCT FROM "bricktracker_metadata_storages"."id"
LEFT JOIN "bricktracker_metadata_purchase_locations"
    ON "bricktracker_individual_part_lots"."purchase_location" IS NOT DISTINCT FROM "bricktracker_metadata_purchase_locations"."id"
WHERE "bricktracker_individual_part_lots"."id" = :id
