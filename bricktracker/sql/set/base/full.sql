{% extends 'set/base/base.sql' %}

{% block id %}
"bricktracker_sets"."id",
{% endblock %}

{% block total_missing %}
IFNULL("problem_join"."total_missing", 0) AS "total_missing",
{% endblock %}

{% block total_damaged %}
IFNULL("problem_join"."total_damaged", 0) AS "total_damaged",
{% endblock %}

{% block total_quantity %}
IFNULL("minifigures_join"."total", 0) AS "total_minifigures"
{% endblock %}

{% block join %}
{% if owners %}
LEFT JOIN "bricktracker_set_owners"
ON "bricktracker_sets"."id" IS NOT DISTINCT FROM "bricktracker_set_owners"."id"
{% endif %}

{% if statuses %}
LEFT JOIN "bricktracker_set_statuses"
ON "bricktracker_sets"."id" IS NOT DISTINCT FROM "bricktracker_set_statuses"."id"
{% endif %}

{% if tags %}
LEFT JOIN "bricktracker_set_tags"
ON "bricktracker_sets"."id" IS NOT DISTINCT FROM "bricktracker_set_tags"."id"
{% endif %}

-- LEFT JOIN + SELECT to avoid messing the total
LEFT JOIN (
    SELECT
        "bricktracker_parts"."id",
        SUM("bricktracker_parts"."missing") AS "total_missing",
        SUM("bricktracker_parts"."damaged") AS "total_damaged"
    FROM "bricktracker_parts"
    {% block where_missing %}{% endblock %}
    GROUP BY "bricktracker_parts"."id"
) "problem_join"
ON "bricktracker_sets"."id" IS NOT DISTINCT FROM "problem_join"."id"

-- LEFT JOIN + SELECT to avoid messing the total
LEFT JOIN (
    SELECT
       "bricktracker_minifigures"."id",
       -- Ни альтернатива, ни counterpart не добавляются к набору:
       -- первая заменяет собой основную позицию, второй собран из уже
       -- посчитанных деталей. В счёт не идут ни та, ни другой
       SUM(CASE WHEN "bricktracker_minifigures"."alternate" = 0
                 AND "bricktracker_minifigures"."counterpart" = 0
                THEN "bricktracker_minifigures"."quantity"
                ELSE 0 END) AS "total"
    FROM "bricktracker_minifigures"
    {% block where_minifigures %}{% endblock %}
    GROUP BY "bricktracker_minifigures"."id"
) "minifigures_join"
ON "bricktracker_sets"."id" IS NOT DISTINCT FROM "minifigures_join"."id"
{% endblock %}