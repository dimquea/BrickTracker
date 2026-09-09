{% extends 'individual_minifigure/base/by_part.sql' %}

{% block condition %}
AND "bricktracker_individual_minifigure_parts"."damaged" > 0
{% endblock %}
