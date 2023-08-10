from dataclasses import dataclass
from jinja2 import Template
from humitifier.urls import Url

from .kvtable import KvTable

 
@dataclass
class HostModal:
    table: KvTable
    template = Template("""
        <div class="modal-wrap">
            <article class="host-modal">
            <main>{{ table.render()|safe }}</main>
            <button hx-swap="none" hx-get="{{ close_url }}"
                    hx-trigger="click, keyup[key=='Escape'] from:body">Close</button>
            </article>
        </div>
    """)

    def render(self) -> str:
        return self.template.render(
            table=self.table,
            close_url=Url.CloseModal.value
        )