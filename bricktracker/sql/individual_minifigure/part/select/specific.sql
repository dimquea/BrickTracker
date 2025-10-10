-- Select a specific part from an individual minifigure instance
SELECT
    "bricktracker_individual_minifigure_parts"."id",
    "bricktracker_individual_minifigures"."figure",
    "bricktracker_individual_minifigure_parts"."part",
    "bricktracker_individual_minifigure_parts"."color",
    "bricktracker_individual_minifigure_parts"."spare",
    "bricktracker_individual_minifigure_parts"."quantity",
    "bricktracker_individual_minifigure_parts"."element",
    "bricktracker_individual_minifigure_parts"."missing",
    "bricktracker_individual_minifigure_parts"."damaged",
    "bricktracker_individual_minifigure_parts"."checked",
    "rebrickable_parts"."color_name",
    "rebrickable_parts"."color_rgb",
    "rebrickable_parts"."color_transparent",
    "rebrickable_parts"."bricklink_color_id",
    "rebrickable_parts"."bricklink_color_name",
    "rebrickable_parts"."bricklink_part_num",
    "rebrickable_parts"."name",
    "rebrickable_parts"."image",
    "rebrickable_parts"."image_id",
    "rebrickable_parts"."url",
    "rebrickable_parts"."print"
FROM "bricktracker_individual_minifigure_parts"
INNER JOIN "bricktracker_individual_minifigures"
ON "bricktracker_individual_minifigure_parts"."id" = "bricktracker_individual_minifigures"."id"
INNER JOIN "rebrickable_parts"
ON "bricktracker_individual_minifigure_parts"."part" = "rebrickable_parts"."part"
AND "bricktracker_individual_minifigure_parts"."color" = "rebrickable_parts"."color_id"
WHERE "bricktracker_individual_minifigure_parts"."id" IS NOT DISTINCT FROM :id
AND "bricktracker_individual_minifigure_parts"."part" IS NOT DISTINCT FROM :part
AND "bricktracker_individual_minifigure_parts"."color" IS NOT DISTINCT FROM :color
AND "bricktracker_individual_minifigure_parts"."spare" IS NOT DISTINCT FROM :spare
