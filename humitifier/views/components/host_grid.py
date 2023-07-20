from dataclasses import dataclass
from jinja2 import Template

from humitifier.models.host_state import HostState
from humitifier.properties import MetadataProperty

GRIDITEM_TEMPLATE = Template("""
<article class = "grid-item">
<header><h3>{{ item.fqdn }}</h3></header>

<ul>
    {% for prop in item.props %}
    <li>{{ prop }}</li>
    {% endfor %}
</ul>

<footer>
    <button hx-swap="none" hx-get="/hx-host-modal/{{ item.fqdn }}">Details</button>
    {% if issue_count %}
    <button hx-swap="none" hx-get="/hx-host-issues/{{ item.fqdn }}">
        {{ item.issue_count }} Issue(s)
    </button>
    {% else %}
    <button disabled>No Issues!</button>
    {% endif %}
</footer>

</article>
""")
                         

@dataclass
class _GridItem:
    fqdn: str
    props: list[str]
    issue_count: int

    @classmethod
    def create(cls, host_state: HostState, properties: list[MetadataProperty]) -> "_GridItem":
        return cls(
            fqdn=host_state.host.fqdn,
            props=[p.kv_atom.render(p.extract(host_state)) for p in properties],
            issue_count=0
        )

    @property
    def html(self) -> str:
        return GRIDITEM_TEMPLATE.render(item=self)


GRID_INNER_TEMPLATE = Template("""
{% for item in items %}
{{ item.html|safe }}
{% endfor %}
""")

GRID_TEMPLATE = Template("""
<section class="grid">
{{ grid.inner_html|safe }}
</section>
""")


@dataclass
class HostGrid:
    items: list[_GridItem]

    @property
    def html(self) -> str:
        return GRID_TEMPLATE.render(grid=self)
    
    @property
    def inner_html(self) -> str:
        return GRID_INNER_TEMPLATE.render(items=self.items)


    @classmethod
    def create(cls, host_states: list[HostState], grid_properties: list[MetadataProperty]) -> "HostGrid":
        items = [_GridItem.create(host_state, grid_properties) for host_state in host_states]
        return cls(items=items)