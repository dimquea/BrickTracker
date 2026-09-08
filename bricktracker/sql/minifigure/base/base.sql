SELECT
    "bricktracker_minifigures"."quantity",
    -- Отметки и признак секции нужны карточке фигурки в наборе
    "bricktracker_minifigures"."missing",
    "bricktracker_minifigures"."damaged",
    "bricktracker_minifigures"."counterpart",
    "bricktracker_minifigures"."alternate",
    "bricktracker_minifigures"."match_id",
    "rebrickable_minifigures"."figure",
    "rebrickable_minifigures"."number",
    "rebrickable_minifigures"."number_of_parts",
    "rebrickable_minifigures"."name",
    "rebrickable_minifigures"."image",
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
    NULL AS "total_sets" -- dummy for order: total_sets
    {% endblock %}
FROM "rebrickable_minifigures"

LEFT JOIN "bricktracker_minifigures"
ON "rebrickable_minifigures"."figure" IS NOT DISTINCT FROM "bricktracker_minifigures"."figure"

{% block join %}{% endblock %}

{% block where %}{% endblock %}

{% block group %}{% endblock %}

{% block having %}{% endblock %}

{% if order %}
ORDER BY {{ order }}
{% endif %}

{% if limit %}
LIMIT {{ limit }}
{% endif %}

{% if offset %}
OFFSET {{ offset }}
{% endif %}
