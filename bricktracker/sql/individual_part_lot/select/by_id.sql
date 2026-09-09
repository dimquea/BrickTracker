SELECT
    "bricktracker_individual_part_lots"."id",
    "bricktracker_individual_part_lots"."name",
    "bricktracker_individual_part_lots"."description",
    "bricktracker_individual_part_lots"."created_date",
    "bricktracker_individual_part_lots"."storage",
    "bricktracker_individual_part_lots"."purchase_location",
    "bricktracker_individual_part_lots"."purchase_date",
    "bricktracker_individual_part_lots"."purchase_price",
    "bricktracker_individual_part_lots"."image",
    "bricktracker_metadata_storages"."name" AS "storage_name",
    "bricktracker_metadata_purchase_locations"."name" AS "purchase_location_name"
    {% if owners %},{{ owners }}{% endif %}
    {% if tags %},{{ tags }}{% endif %}
FROM "bricktracker_individual_part_lots"
LEFT JOIN "bricktracker_metadata_storages"
    ON "bricktracker_individual_part_lots"."storage" IS NOT DISTINCT FROM "bricktracker_metadata_storages"."id"
LEFT JOIN "bricktracker_metadata_purchase_locations"
    ON "bricktracker_individual_part_lots"."purchase_location" IS NOT DISTINCT FROM "bricktracker_metadata_purchase_locations"."id"

LEFT JOIN "bricktracker_set_owners"
ON "bricktracker_individual_part_lots"."id" IS NOT DISTINCT FROM "bricktracker_set_owners"."id"

-- Note: Part lots don't have statuses, only owners and tags

LEFT JOIN "bricktracker_set_tags"
ON "bricktracker_individual_part_lots"."id" IS NOT DISTINCT FROM "bricktracker_set_tags"."id"

WHERE "bricktracker_individual_part_lots"."id" = :id
