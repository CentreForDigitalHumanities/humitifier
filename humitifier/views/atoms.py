from dataclasses import dataclass
from jinja2 import Template

from humitifier.models.person import Person
from humitifier.protocols import IAtom

@dataclass
class ProgressBar(IAtom):
    description: str
    value: int
    template = Template("""
        <div class="progress" data-label="{{props.description}}">
            <span class="value" style="width:{{props.value}}%;"></span>
        </div>"""
    )

    def render(self) -> str:
        return self.template.render(props=self)


@dataclass
class MailToPerson(IAtom):
    person: Person
    template = Template("""
        <a href="mailto:{{ props.email }}">{{ props.name }}</a>
        {% if props.notes %}
        <abbr title="{{ props.notes }}">🛈</abbr>
        {% endif %}
        """)

    def render(self) -> str:
        return self.template.render(props=self.person)
    

@dataclass
class UnorderedList:
    items: list[str]
    template = Template("""
        <ul>
            {% for item_html in props.items %}
            <li>{{ item_html|safe }}</li>
            {% endfor %}
        </ul>"""
    )

    def render(self) -> str:
        return self.template.render(props=self)
    

@dataclass
class InlineList(IAtom):
    items: list[str]
    template = Template("""
        <ul class=inline-list>
            {% for item_html in props.items %}
            <li>{{ item_html }}</li>
            {% endfor %}
        </ul>"""
    )

    def render(self) -> str:
        return self.template.render(props=self)