BEGIN TRANSACTION;

ALTER TABLE "bricktracker_set_owners"
DROP COLUMN "owner_{{ id }}";

-- Also drop from wishes
ALTER TABLE "bricktracker_wish_owners"
DROP COLUMN "owner_{{ id }}";

-- Also drop from individual minifigures
ALTER TABLE "bricktracker_individual_minifigure_owners"
DROP COLUMN "owner_{{ id }}";

-- Also drop from individual parts
ALTER TABLE "bricktracker_individual_part_owners"
DROP COLUMN "owner_{{ id }}";

-- Also drop from individual part lots
ALTER TABLE "bricktracker_individual_part_lot_owners"
DROP COLUMN "owner_{{ id }}";

DELETE FROM "bricktracker_metadata_owners"
WHERE "bricktracker_metadata_owners"."id" IS NOT DISTINCT FROM '{{ id }}';

COMMIT;