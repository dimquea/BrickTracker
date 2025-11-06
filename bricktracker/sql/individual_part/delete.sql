-- Delete metadata first (foreign keys with CASCADE will handle this, but being explicit)
DELETE FROM "bricktracker_individual_part_owners"
WHERE "id" = '{{ id }}';

DELETE FROM "bricktracker_individual_part_tags"
WHERE "id" = '{{ id }}';

DELETE FROM "bricktracker_individual_part_statuses"
WHERE "id" = '{{ id }}';

-- Delete the individual part itself
DELETE FROM "bricktracker_individual_parts"
WHERE "id" = '{{ id }}';
