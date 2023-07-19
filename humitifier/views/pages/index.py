from dataclasses import dataclass
from jinja2 import Template
from humitifier.config import AppConfig
from humitifier.models.host_state import HostState
from humitifier.views.components.host_grid import HostGrid
from humitifier.views.components.host_filterset import FilterSet

TEMPLATE = Template("""
<section id="host-grid-page">
    <header class="main-header">
        <img src="static/img/uu-rgb-black.png" alt="logo" class="logo">
        <main>
            <h1>Monitor Servers, <br /><em>Mess up less</em></h1>
        </main>
        <aside></aside>
    </header>          
    {{ filterset.html|safe }}
    <article id="hx-modal"></article>
    {{ grid.html|safe }}
</section>
""")


@dataclass
class HostGridIndex:
    grid: HostGrid
    filterset: FilterSet

    @property
    def html(self) -> str:
        return TEMPLATE.render(grid=self.grid, filterset=self.filterset)
    
    @classmethod
    def create(cls, host_states: list[HostState], app_config: AppConfig) -> "HostGridIndex":
        grid = HostGrid.create(host_states=host_states, grid_properties=app_config.grid_properties)
        filterset = FilterSet.create(host_states=host_states, filters=app_config.filters)
        return cls(grid=grid, filterset=filterset)