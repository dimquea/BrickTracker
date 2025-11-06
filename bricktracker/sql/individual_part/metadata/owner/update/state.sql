INSERT INTO "bricktracker_individual_part_owners" (
    "id",
    "{{name}}"
) VALUES (
    :id,
    :state
)
ON CONFLICT("id")
DO UPDATE SET "{{name}}" = :state
WHERE "bricktracker_individual_part_owners"."id" IS NOT DISTINCT FROM :id
