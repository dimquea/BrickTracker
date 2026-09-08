UPDATE "bricktracker_minifigures"
SET "missing" = :missing
WHERE "bricktracker_minifigures"."id" IS NOT DISTINCT FROM :id
AND "bricktracker_minifigures"."figure" IS NOT DISTINCT FROM :figure
