INSERT INTO "bricktracker_individual_part_statuses" (
    "id",
    "{{name}}"
) VALUES (
    :id,
    :state
)
ON CONFLICT("id")
DO UPDATE SET "{{name}}" = :state
WHERE "bricktracker_individual_part_statuses"."id" IS NOT DISTINCT FROM :id
