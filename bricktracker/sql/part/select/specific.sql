{% extends 'part/base/base.sql' %}

{% block where %}
WHERE "combined"."id" IS NOT DISTINCT FROM :id
AND "combined"."figure" IS NOT DISTINCT FROM :figure
AND "combined"."part" IS NOT DISTINCT FROM :part
AND "combined"."color" IS NOT DISTINCT FROM :color
AND "combined"."spare" IS NOT DISTINCT FROM :spare
{% endblock %}

{% block group %}
GROUP BY
    "combined"."id",
    "combined"."figure",
    "combined"."part",
    "combined"."color",
    "combined"."spare"
{% endblock %}
