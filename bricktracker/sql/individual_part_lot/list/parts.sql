SELECT
    "bricktracker_individual_parts"."id",
    "bricktracker_individual_parts"."part",
    "bricktracker_individual_parts"."color",
    "bricktracker_individual_parts"."quantity",
    "bricktracker_individual_parts"."missing",
    "bricktracker_individual_parts"."damaged",
    "bricktracker_individual_parts"."checked",
    "bricktracker_individual_parts"."description",
    "bricktracker_individual_parts"."storage",
    "bricktracker_individual_parts"."purchase_location",
    "bricktracker_individual_parts"."purchase_date",
    "bricktracker_individual_parts"."purchase_price",
    "bricktracker_individual_parts"."lot_id",
    "rebrickable_parts"."name",
    "rebrickable_parts"."color_name",
    "rebrickable_parts"."color_rgb",
    "rebrickable_parts"."color_transparent",
    "rebrickable_parts"."image",
    "rebrickable_parts"."url"
FROM "bricktracker_individual_parts"
INNER JOIN "rebrickable_parts"
    ON "bricktracker_individual_parts"."part" = "rebrickable_parts"."part"
    AND "bricktracker_individual_parts"."color" = "rebrickable_parts"."color_id"
WHERE "bricktracker_individual_parts"."lot_id" = :lot_id
ORDER BY "rebrickable_parts"."name" ASC, "bricktracker_individual_parts"."color" ASC
