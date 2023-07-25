from dataclasses import dataclass
from jinja2 import Template
from typing import Literal
from humitifier.filters import filter_options
from humitifier.models.host_state import HostState
from humitifier.protocols import IFilter
from typing import Type

FILTER_TEMPLATE = Template("""
<article>
    {% if filter.widget == "select" %}

    <select id="{{ filter.slug }}-input" name="{{ filter.slug }}">
        <option value="" selected>Select {{ filter.label }}...</option>
        {% for opt in filter.options %}
        <option value="{{ opt }}">{{ opt }}</option>
        {% endfor %}
    </select>

    {% elif filter.widget == "search" %}

    <input list="{{ filter.slug }}-suggestions" id="{{ filter.slug }}-input" type="text" name="{{ filter.slug }}"
        placeholder="search {{ filter.label }}..." />
    <datalist id="{{ filter.slug }}-suggestions">
        {% for suggestion in filter.options %}
        <option value="{{ suggestion }}">
            {% endfor %}
    </datalist>

    {% endif %}
</article>
""")
                           
FILTERSET_TEMPLATE = Template("""
<form class="filterset" hx-get="/hx-filter-hosts" hx-swap="none"
    hx-trigger="submit, {% for f in filters %}input from:#{{f.slug}}-input delay:0s,{% endfor %}">
    {% for filter in filters %}
    {{ filter.html|safe }}
    {% endfor %}
</form>
""")

@dataclass
class _Filter:
    slug: str
    label: str
    options: str
    widget: Literal["select", "search"]

    @property
    def html(self) -> str:
        return FILTER_TEMPLATE.render(filter=self)
    
    @classmethod
    def create(cls, filter: Type[IFilter], host_states: list[HostState]) -> "_Filter":
        options = filter_options(filter.options(host_states))
        return cls(slug=filter.slug, label=filter.label, options=options, widget=filter.widget)
    

@dataclass
class FilterSet:
    filters: list[_Filter]

    @property
    def html(self) -> str:
        return FILTERSET_TEMPLATE.render(filters=self.filters)

    @classmethod
    def create(cls, filters: list[Type[IFilter]], host_states: list[HostState]) -> "FilterSet":
        _filters = [_Filter.create(filter, host_states) for filter in filters]
        return cls(filters=_filters)
