import pytest
from humitifier.config import AppConfig
from humitifier.filters import Filter
from humitifier.properties import MetadataProperty, FactProperty
from humitifier.views.components.host_grid import HostGrid
from humitifier.views.components.host_filterset import FilterSet
from humitifier.views.components.host_modal import HostModal
from humitifier.views.pages.index import HostGridIndex
from humitifier.views.utils import Atom, Wrapper
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


@pytest.mark.parametrize(
    "atom, properties", [
        (Atom.String, "foo"),
        (Atom.Progress, {"description": "foo", "value": 50}),
        (Atom.MailToPerson, FakePerson.generate()),
        (Atom.MailToPeopleList, [FakePerson.generate()]),
        (Atom.InlineListStrings, ["foo", "bar"]),
        (Atom.InlineListPackages, [FakePackage.generate()]),
        (Atom.DaysString, 5),
        (Atom.MegaBytesString, 1024),
])
def test_atom_render_ok(atom, properties):
    assert isinstance(atom.render(properties), str)


@pytest.mark.parametrize(
    "atom, properties", [
        (Atom.Progress, {}),
        (Atom.MailToPerson, {}),
        (Atom.MailToPeopleList, FakePerson.generate()),
        (Atom.MailToPeopleList, ["yoohoo"]),
        (Atom.InlineListStrings, 1),
        (Atom.InlineListStrings, [1]),
        (Atom.InlineListPackages, 1),
        (Atom.InlineListPackages, ["foo"]),
        (Atom.DaysString, "5"),
        (Atom.MegaBytesString, "1024"),
])
def test_atom_render_value_error(atom, properties):
    with pytest.raises(ValueError):
        atom.render(properties)


@pytest.mark.parametrize("filters", [[], [f for f in Filter]])
@pytest.mark.parametrize("states", [[], [FakeHostState.generate() for _ in range(10)]])
def test_host_filterset_create(filters, states):
    fs = FilterSet.create(filters=filters, host_states=states)
    assert isinstance(fs, FilterSet)
    assert isinstance(fs.html, str)


@pytest.mark.parametrize("states", [[], [FakeHostState.generate() for _ in range(10)]])
@pytest.mark.parametrize("properties", [[], [p for p in MetadataProperty], [p for p in FactProperty], [p for p in MetadataProperty] + [p for p in FactProperty]])
def test_host_grid_create(states, properties):
    hg = HostGrid.create(host_states=states, grid_properties=properties)
    assert isinstance(hg, HostGrid)
    assert isinstance(hg.html, str)
    assert isinstance(hg.inner_html, str)


@pytest.mark.parametrize("metadata_properties", [[], [p for p in MetadataProperty]])
@pytest.mark.parametrize("fact_properties", [[], [p for p in FactProperty]])
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