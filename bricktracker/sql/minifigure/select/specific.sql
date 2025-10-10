{% extends 'minifigure/base/base.sql' %}

{% block where %}
WHERE "combined"."id" IS NOT DISTINCT FROM :id
AND "combined"."figure" IS NOT DISTINCT FROM :figure
AND "combined"."source_type" = 'set'
{% endblock %}
