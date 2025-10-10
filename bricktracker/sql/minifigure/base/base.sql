-- Combined query for both set-based and individual minifigures
SELECT
    "combined"."quantity",
    "combined"."figure",
    "combined"."number",
    "combined"."number_of_parts",
    "combined"."name",
    "combined"."image",
    {% block total_missing %}
    NULL AS "total_missing", -- dummy for order: total_missing
    {% endblock %}
    {% block total_damaged %}
    NULL AS "total_damaged", -- dummy for order: total_damaged
    {% endblock %}
    {% block total_quantity %}
    NULL AS "total_quantity", -- dummy for order: total_quantity
    {% endblock %}
    {% block total_sets %}
    NULL AS "total_sets", -- dummy for order: total_sets
    {% endblock %}
    {% block total_individual %}
    NULL AS "total_individual" -- dummy for order: total_individual
    {% endblock %}
FROM (
    -- Set-based minifigures
    SELECT
        "bricktracker_minifigures"."id",
        "bricktracker_minifigures"."quantity",
        "rebrickable_minifigures"."figure",
        "rebrickable_minifigures"."number",
        "rebrickable_minifigures"."number_of_parts",
        "rebrickable_minifigures"."name",
        "rebrickable_minifigures"."image",
        "bricktracker_minifigures"."rowid" AS "rowid",
        'set' AS "source_type"
    FROM "bricktracker_minifigures"
    INNER JOIN "rebrickable_minifigures"
    ON "bricktracker_minifigures"."figure" IS NOT DISTINCT FROM "rebrickable_minifigures"."figure"

    UNION ALL

    -- Individual minifigures
    SELECT
        "bricktracker_individual_minifigures"."id",
        "bricktracker_individual_minifigures"."quantity",
        "rebrickable_minifigures"."figure",
        "rebrickable_minifigures"."number",
        "rebrickable_minifigures"."number_of_parts",
        "rebrickable_minifigures"."name",
        "rebrickable_minifigures"."image",
        "bricktracker_individual_minifigures"."rowid" AS "rowid",
        'individual' AS "source_type"
    FROM "bricktracker_individual_minifigures"
    INNER JOIN "rebrickable_minifigures"
    ON "bricktracker_individual_minifigures"."figure" IS NOT DISTINCT FROM "rebrickable_minifigures"."figure"
) AS "combined"

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
