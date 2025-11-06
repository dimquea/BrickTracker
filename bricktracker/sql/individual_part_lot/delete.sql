-- Delete all individual parts associated with this lot
DELETE FROM "bricktracker_individual_parts"
WHERE "lot_id" = :id;

-- Delete lot owners
DELETE FROM "bricktracker_individual_part_lot_owners"
WHERE "id" = :id;

-- Delete lot tags
DELETE FROM "bricktracker_individual_part_lot_tags"
WHERE "id" = :id;

-- Delete the lot itself
DELETE FROM "bricktracker_individual_part_lots"
WHERE "id" = :id;
