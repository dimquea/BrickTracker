UPDATE "bricktracker_minifigures"
SET "damaged" = :damaged
WHERE "bricktracker_minifigures"."id" IS NOT DISTINCT FROM :id
AND "bricktracker_minifigures"."figure" IS NOT DISTINCT FROM :figure
