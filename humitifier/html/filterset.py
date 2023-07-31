from dataclasses import dataclass
from jinja2 import Template

from .input_search import SearchInput
from .input_select import SelectInput


_hx_triggers = Template("""
    {% for t in triggers %}input from:#{{t}}-input delay:0s,{% endfor %}
""")

@dataclass
class FilterSet:
    url: str
    widgets: list[SearchInput | SelectInput]
    template = Template("""
        <form class="filterset" hx-get="{{url}}" hx-swap="none"
            hx-trigger="submit, {{trigger_html|safe}}">
            {% for widget in widgets %}
            {{ widget.render()|safe }}
            {% endfor %}
        </form>
    """)

    def render(self) -> str:
        triggers = [w.name for w in self.widgets]
        trigger_html = _hx_triggers.render(triggers=triggers)
        return self.template.render(
            widgets=self.widgets,
            trigger_html=trigger_html,
            url=self.url
        )