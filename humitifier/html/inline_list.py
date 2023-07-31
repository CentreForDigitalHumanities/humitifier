from dataclasses import dataclass
from jinja2 import Template
from .protocols import HtmlComponent

@dataclass
class InlineList:
    items: list[HtmlComponent]
    template = Template("""
        <ul class=inline-list>
            {% for item in items %}
            <li>{{ item.render()|safe }}</li>
            {% endfor %}
        </ul>"""
    )

    def render(self) -> str:
        return self.template.render(items=self.items)