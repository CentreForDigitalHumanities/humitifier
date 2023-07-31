from dataclasses import dataclass
from jinja2 import Template
from .protocols import HtmlComponent

@dataclass
class KvRow:
    label: str
    value: HtmlComponent
    template = Template("""
        <tr class="kv-table-row">
            <td>{{ label }}</td>
            <td>{{ value.render()|safe }}</td>
        </tr>"""
    )

    def render(self) -> str:
        return self.template.render(
            label=self.label, 
            value=self.value
        )