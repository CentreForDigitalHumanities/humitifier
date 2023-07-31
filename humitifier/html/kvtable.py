from dataclasses import dataclass
from jinja2 import Template
from .kvrow import KvRow

@dataclass
class KvTable:
    rows: list[KvRow]
    template = Template("""
        <table>
            <tbody>
                {% for row in rows %}
                {{ row.render()|safe }}
                {% endfor %}
            </tbody>
        </table>
        """)
    
    def render(self) -> str:
        return self.template.render(rows=self.rows)