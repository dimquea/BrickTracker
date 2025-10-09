-- Query parts from both set-based and individual minifigures
SELECT
    "parts_combined"."id",
    "parts_combined"."figure",
    "parts_combined"."part",
    "parts_combined"."color",
    "parts_combined"."spare",
    SUM("parts_combined"."quantity") AS "quantity",
    "parts_combined"."element",
    SUM("parts_combined"."missing") AS "total_missing",
    SUM("parts_combined"."damaged") AS "total_damaged",
    MAX("parts_combined"."checked") AS "checked",
    "rebrickable_parts"."color_name",
    "rebrickable_parts"."color_rgb",
    "rebrickable_parts"."color_transparent",
    "rebrickable_parts"."bricklink_color_id",
    "rebrickable_parts"."bricklink_color_name",
    "rebrickable_parts"."bricklink_part_num",
    "rebrickable_parts"."name",
    "rebrickable_parts"."image",
    "rebrickable_parts"."image_id",
    "rebrickable_parts"."url",
    "rebrickable_parts"."print",
    NULL AS "total_quantity",
    NULL AS "total_spare",
    NULL AS "total_sets",
    NULL AS "total_minifigures"
FROM (
    -- Set-based minifigure parts
    SELECT
        "bricktracker_parts"."id",
        "bricktracker_parts"."figure",
        "bricktracker_parts"."part",
        "bricktracker_parts"."color",
        "bricktracker_parts"."spare",
        "bricktracker_parts"."quantity",
        "bricktracker_parts"."element",
        "bricktracker_parts"."missing",
        "bricktracker_parts"."damaged",
        "bricktracker_parts"."checked"
    FROM "bricktracker_parts"
    WHERE "bricktracker_parts"."figure" IS NOT DISTINCT FROM :figure

    UNION ALL

    -- Individual minifigure parts
    SELECT
        "bricktracker_individual_minifigure_parts"."id",
        "bricktracker_individual_minifigures"."figure",
        "bricktracker_individual_minifigure_parts"."part",
        "bricktracker_individual_minifigure_parts"."color",
        "bricktracker_individual_minifigure_parts"."spare",
        "bricktracker_individual_minifigure_parts"."quantity",
        "bricktracker_individual_minifigure_parts"."element",
        "bricktracker_individual_minifigure_parts"."missing",
        "bricktracker_individual_minifigure_parts"."damaged",
        "bricktracker_individual_minifigure_parts"."checked"
    FROM "bricktracker_individual_minifigure_parts"
    INNER JOIN "bricktracker_individual_minifigures"
    ON "bricktracker_individual_minifigure_parts"."id" = "bricktracker_individual_minifigures"."id"
    WHERE "bricktracker_individual_minifigures"."figure" IS NOT DISTINCT FROM :figure
) AS "parts_combined"

INNER JOIN "rebrickable_parts"
ON "parts_combined"."part" = "rebrickable_parts"."part"
AND "parts_combined"."color" = "rebrickable_parts"."color_id"

GROUP BY
    "parts_combined"."part",
    "parts_combined"."color",
    "parts_combined"."spare",
    "parts_combined"."element",
    "rebrickable_parts"."color_name",
    "rebrickable_parts"."color_rgb",
    "rebrickable_parts"."color_transparent",
    "rebrickable_parts"."bricklink_color_id",
    "rebrickable_parts"."bricklink_color_name",
    "rebrickable_parts"."bricklink_part_num",
    "rebrickable_parts"."name",
    "rebrickable_parts"."image",
    "rebrickable_parts"."image_id",
    "rebrickable_parts"."url",
    "rebrickable_parts"."print"

{% if order %}
-- Replace combined/bricktracker_parts references with parts_combined for this query
ORDER BY {{ order | replace('"combined"', '"parts_combined"') | replace('"bricktracker_parts"', '"parts_combined"') }}
{% endif %}
