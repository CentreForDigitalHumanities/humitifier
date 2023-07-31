from dataclasses import dataclass
from jinja2 import Template

@dataclass
class MailTo:
    name: str
    email: str
    info: str | None = None

    template = Template("""
        <a href="mailto:{{ email }}">{{ name }}</a>
        {% if info %}
        <abbr title="{{ info }}">🛈</abbr>
        {% endif %}
        """)

    def render(self) -> str:
        return self.template.render(
            name=self.name,
            email=self.email,
            info=self.info,
        )