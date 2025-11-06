SELECT
    "combined"."id",
    "combined"."figure",
    "combined"."part",
    "combined"."color",
    "combined"."spare",
    "combined"."quantity",
    "combined"."element",
    "combined"."missing",
    "combined"."damaged",
    "combined"."checked",
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
    {% block total_missing %}
    NULL AS "total_missing", -- dummy for order: total_missing
    {% endblock %}
    {% block total_damaged %}
    NULL AS "total_damaged", -- dummy for order: total_damaged
    {% endblock %}
    {% block total_quantity %}
    NULL AS "total_quantity", -- dummy for order: total_quantity
    {% endblock %}
    {% block total_spare %}
    NULL AS "total_spare", -- dummy for order: total_spare
    {% endblock %}
    {% block total_sets %}
    NULL AS "total_sets", -- dummy for order: total_sets
    {% endblock %}
    {% block total_minifigures %}
    NULL AS "total_minifigures" -- dummy for order: total_minifigures
    {% endblock %}
FROM (
    -- Parts from set-based minifigures
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
        "bricktracker_parts"."checked",
        'set' AS "source_type"
    FROM "bricktracker_parts"

    UNION ALL

    -- Parts from individual minifigures
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
        "bricktracker_individual_minifigure_parts"."checked",
        'individual_minifigure' AS "source_type"
    FROM "bricktracker_individual_minifigure_parts"
    INNER JOIN "bricktracker_individual_minifigures"
    ON "bricktracker_individual_minifigure_parts"."id" = "bricktracker_individual_minifigures"."id"

    UNION ALL

    -- Individual/standalone parts (not from any set or minifigure)
    SELECT
        "bricktracker_individual_parts"."id",
        NULL AS "figure",
        "bricktracker_individual_parts"."part",
        "bricktracker_individual_parts"."color",
        0 AS "spare",
        "bricktracker_individual_parts"."quantity",
        NULL AS "element",
        "bricktracker_individual_parts"."missing",
        "bricktracker_individual_parts"."damaged",
        "bricktracker_individual_parts"."checked",
        'individual_part' AS "source_type"
    FROM "bricktracker_individual_parts"
) AS "combined"

INNER JOIN "rebrickable_parts"
ON "combined"."part" IS NOT DISTINCT FROM "rebrickable_parts"."part"
AND "combined"."color" IS NOT DISTINCT FROM "rebrickable_parts"."color_id"

{% block join %}{% endblock %}

{% block where %}{% endblock %}

{% block group %}{% endblock %}

{% if order %}
ORDER BY {{ order }}
{% endif %}

{% if limit %}
LIMIT {{ limit }}
{% endif %}

{% if offset %}
OFFSET {{ offset }}
{% endif %}
