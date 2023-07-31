from dataclasses import dataclass
from jinja2 import Template
from .protocols import HtmlComponent

@dataclass
class UnorderedList:
    items: list[HtmlComponent]
    template = Template("""
        <ul>
            {% for item in items %}
            <li>{{ item|safe }}</li>
            {% endfor %}
        </ul>"""
    )

    def render(self) -> str:
        return self.template.render(items=self.items)