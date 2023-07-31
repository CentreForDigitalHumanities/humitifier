from dataclasses import dataclass
from jinja2 import Template


@dataclass
class SearchInput:
    name: str
    label: str
    options: set[str]
    
    template = Template("""
        <input list="{{ name }}-suggestions" id="{{ name }}-input" type="text" name="{{ name }}"
            placeholder="search {{ label }}..." />
        datalist id="{{ name }}-suggestions">
            {% for opt in options %}
            <option value="{{ opt }}">{{ opt }}</option>
            {% endfor %}
        </datalist>
    """)

    def render(self) -> str:
        return self.template.render(
            name=self.name,
            label=self.label,
            options=sorted(self.options)
        )