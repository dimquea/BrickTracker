-- Delete individual minifigure parts
DELETE FROM "bricktracker_individual_minifigure_parts"
WHERE "id" = :id;

-- Delete individual minifigure owners
DELETE FROM "bricktracker_individual_minifigure_owners"
WHERE "id" = :id;

-- Delete individual minifigure tags
DELETE FROM "bricktracker_individual_minifigure_tags"
WHERE "id" = :id;

-- Delete individual minifigure statuses
DELETE FROM "bricktracker_individual_minifigure_statuses"
WHERE "id" = :id;

-- Delete the individual minifigure itself
DELETE FROM "bricktracker_individual_minifigures"
WHERE "id" = :id;
