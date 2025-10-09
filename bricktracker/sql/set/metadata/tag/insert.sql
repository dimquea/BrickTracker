BEGIN TRANSACTION;

ALTER TABLE "bricktracker_set_tags"
ADD COLUMN "tag_{{ id }}" BOOLEAN NOT NULL DEFAULT 0;

-- Also inject into individual minifigures
ALTER TABLE "bricktracker_individual_minifigure_tags"
ADD COLUMN "tag_{{ id }}" BOOLEAN NOT NULL DEFAULT 0;

-- Also inject into individual parts
ALTER TABLE "bricktracker_individual_part_tags"
ADD COLUMN "tag_{{ id }}" BOOLEAN NOT NULL DEFAULT 0;

INSERT INTO "bricktracker_metadata_tags" (
    "id",
    "name"
) VALUES (
    '{{ id }}',
    '{{ name }}'
);

COMMIT;