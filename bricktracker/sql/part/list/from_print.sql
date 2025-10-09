
{% extends 'part/base/base.sql' %}

{% block total_missing %}{% endblock %}

{% block total_damaged %}{% endblock %}

{% block where %}
WHERE "rebrickable_parts"."print" IS NOT DISTINCT FROM :print
AND "combined"."color" IS NOT DISTINCT FROM :color
AND "combined"."part" IS DISTINCT FROM :part
{% endblock %}

{% block group %}
GROUP BY
    "combined"."part",
    "combined"."color"
{% endblock %}
