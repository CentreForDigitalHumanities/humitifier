from dataclasses import dataclass
from jinja2 import Template


@dataclass
class SelectInput:
    name: str
    label: str
    options: set[str]
    
    template = Template("""
        <select id="{{ name }}-input" name="{{ name }}">
            <option value="" selected>Select {{ label }}...</option>
            {% for opt in options %}
            <option value="{{ opt }}">{{ opt }}</option>
            {% endfor %}
        </select>"""
    )

    def render(self) -> str:
        return self.template.render(
            name=self.name,
            label=self.label,
            options=sorted(self.options)
        )