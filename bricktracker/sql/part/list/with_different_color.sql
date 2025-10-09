
{% extends 'part/base/base.sql' %}

{% block total_missing %}{% endblock %}

{% block total_damaged %}{% endblock %}

{% block where %}
WHERE "combined"."color" IS DISTINCT FROM :color
AND "combined"."part" IS NOT DISTINCT FROM :part
{% endblock %}

{% block group %}
GROUP BY
    "combined"."part",
    "combined"."color"
{% endblock %}
