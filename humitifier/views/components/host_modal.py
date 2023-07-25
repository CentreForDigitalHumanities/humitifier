from dataclasses import dataclass
from jinja2 import Template
from humitifier.models.host_state import HostState

from humitifier.protocols import IProperty

from typing import Type



KV_TABLE_TEMPLATE = Template("""
<table>
    <tbody>
        {% for key, value_html in items %}
        <tr class="kv-table-row">
            <td>{{ key }}</td>
            <td>{{ value_html|safe }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
""")

@dataclass
class _KvTable:
    items: list[tuple[str, str]]

    @property
    def html(self) -> str:
        return KV_TABLE_TEMPLATE.render(items=self.items)
    
    @classmethod
    def create(cls, host_state: HostState, properties: list[Type[IProperty]]) -> "_KvTable":
        props = [prop.from_host_state(host_state) for prop in properties]
        items = ((prop.kv_label, prop.render_kv_value()) for prop in props)
        return cls(items=items)



HOST_MODAL_TEMPLATE = Template("""
<div class="modal-wrap">
    <article class="host-modal">
    <main>{{ fact_kv.html|safe }}</main>
    <aside>{{ meta_kv.html|safe }}</aside>
    <button hx-swap="none" hx-get="/hx-clear-host-modal"
            hx-trigger="click, keyup[key=='Escape'] from:body">Close</button>
    </article>
</div>
""")
                               

@dataclass
class HostModal:
    meta_kv: _KvTable
    fact_kv: _KvTable

    @property
    def html(self) -> str:
        return HOST_MODAL_TEMPLATE.render(meta_kv=self.meta_kv, fact_kv=self.fact_kv)
    
    @classmethod
    def create(cls, host_state: HostState, metadata_properties: list[Type[IProperty]], fact_properties: list[Type[IProperty]]) -> "HostModal":
        meta_kv = _KvTable.create(host_state, metadata_properties)
        fact_kv = _KvTable.create(host_state, fact_properties)
        return cls(meta_kv=meta_kv, fact_kv=fact_kv)


