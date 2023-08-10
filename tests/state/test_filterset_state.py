import pytest
from humitifier.html import SelectInput, SearchInput, FilterSet
from humitifier.state.filterset import HostStateFilterset


@pytest.mark.parametrize("widgets", [
    [SelectInput(name="select", label="test", options=["test"])],
    [SearchInput(name="search", label="test", options=["test"])],
    [],
    [
        SelectInput(name="select", label="test", options=["test"]),
        SearchInput(name="search", label="test", options=["test"]),
    ]
])
def test_filterset_component(widgets):
    filterset = HostStateFilterset(widgets, None)
    assert isinstance(filterset.component(FilterSet), FilterSet)