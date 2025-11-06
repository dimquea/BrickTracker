BEGIN TRANSACTION;

ALTER TABLE "bricktracker_set_tags"
DROP COLUMN "tag_{{ id }}";

-- Also drop from individual minifigures
ALTER TABLE "bricktracker_individual_minifigure_tags"
DROP COLUMN "tag_{{ id }}";

-- Also drop from individual parts
ALTER TABLE "bricktracker_individual_part_tags"
DROP COLUMN "tag_{{ id }}";

-- Also drop from individual part lots
ALTER TABLE "bricktracker_individual_part_lot_tags"
DROP COLUMN "tag_{{ id }}";

DELETE FROM "bricktracker_metadata_tags"
WHERE "bricktracker_metadata_tags"."id" IS NOT DISTINCT FROM '{{ id }}';

COMMIT;