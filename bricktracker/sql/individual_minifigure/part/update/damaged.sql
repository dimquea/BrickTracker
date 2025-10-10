UPDATE "bricktracker_individual_minifigure_parts"
SET "damaged" = :damaged
WHERE "bricktracker_individual_minifigure_parts"."id" IS NOT DISTINCT FROM :id
AND "bricktracker_individual_minifigure_parts"."part" IS NOT DISTINCT FROM :part
AND "bricktracker_individual_minifigure_parts"."color" IS NOT DISTINCT FROM :color
AND "bricktracker_individual_minifigure_parts"."spare" IS NOT DISTINCT FROM :spare
