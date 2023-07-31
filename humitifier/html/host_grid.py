from dataclasses import dataclass
from jinja2 import Template
from .host_card import HostCard


@dataclass
class HostGridItems:
    items: list[HostCard]
    template = Template("""
    {% for item in items %}
    {{ item.render()|safe }}
    {% endfor %}
    """)

    def render(self) -> str:
        return self.template.render(items=self.items)


@dataclass
class HostGrid:
    items: HostGridItems
    template = Template("""
    <section class="grid">
    {{ items.render()|safe }}
    </section>
    """)

    def render(self) -> str:
        return self.template.render(items=self.items)