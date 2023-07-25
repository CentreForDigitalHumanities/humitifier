import pytest
from humitifier.config import AppConfig, DEFAULT_FACTPROPS, DEFAULT_FILTERS, DEFAULT_METAPROPS, DEFAULT_FACTS
from humitifier.views.components.host_grid import HostGrid
from humitifier.views.components.host_filterset import FilterSet
from humitifier.views.components.host_modal import HostModal
from humitifier.views.pages.index import HostGridIndex
from humitifier.views.utils import Wrapper
from humitifier.fake.gen.host_state import FakeHostState
from humitifier.fake.gen.person import FakePerson
from humitifier.fake.gen.facts import FakePackage


def test_wrapper_render_ok():
    html = "<html></html>"
    target = "innerHTML:#target"
    assert Wrapper.HxOobSwap.render(html_content=html, target=target)
    assert Wrapper.Base.render(html_content=html)


def test_wrapper_raises_error_on_invalid_properties():
    with pytest.raises(ValueError):
        Wrapper.HxOobSwap.render(html_content="")




@pytest.mark.parametrize("filters", [[], DEFAULT_FILTERS])
@pytest.mark.parametrize("states", [[], [FakeHostState.generate() for _ in range(10)]])
def test_host_filterset_create(filters, states):
    fs = FilterSet.create(filters=filters, host_states=states)
    assert isinstance(fs, FilterSet)
    assert isinstance(fs.html, str)


@pytest.mark.parametrize("states", [[], [FakeHostState.generate() for _ in range(10)]])
@pytest.mark.parametrize("properties", [[], DEFAULT_FACTPROPS, DEFAULT_METAPROPS, DEFAULT_METAPROPS + DEFAULT_FACTPROPS])
def test_host_grid_create(states, properties):
    hg = HostGrid.create(host_states=states, grid_properties=properties)
    assert isinstance(hg, HostGrid)
    assert isinstance(hg.html, str)
    assert isinstance(hg.inner_html, str)


@pytest.mark.parametrize("metadata_properties", [[], DEFAULT_METAPROPS])
@pytest.mark.parametrize("fact_properties", [[], DEFAULT_FACTPROPS])
def test_host_modal_create(metadata_properties, fact_properties):
    hm = HostModal.create(host_state=FakeHostState.generate(), metadata_properties=metadata_properties, fact_properties=fact_properties)
    assert isinstance(hm, HostModal)
    assert isinstance(hm.html, str)


def test_index_create_with_default_config():
    states = [FakeHostState.generate() for _ in range(10)]
    config = AppConfig.default(hosts=[s.host for s in states])
    index = HostGridIndex.create(host_states=states, app_config=config)
    assert isinstance(index, HostGridIndex)
    assert isinstance(index.html, str)
    assert isinstance(index.grid, HostGrid)
    assert isinstance(index.filterset, FilterSet)