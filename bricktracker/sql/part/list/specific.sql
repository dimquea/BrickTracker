
{% extends 'part/base/base.sql' %}

{% block total_missing %}
IFNULL("combined"."missing", 0) AS "total_missing",
{% endblock %}

{% block total_damaged %}
IFNULL("combined"."damaged", 0) AS "total_damaged",
{% endblock %}

{% block where %}
WHERE "combined"."id" IS NOT DISTINCT FROM :id
AND "combined"."figure" IS NOT DISTINCT FROM :figure
{% endblock %}
