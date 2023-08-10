import pytest
from humitifier.html import HtmlString, KvRow
from humitifier.props import Os
from humitifier.props.protocols import Property, Filterable


def test_os_implements_prop_protocol():
    assert isinstance(Os, Property)


def test_os_implements_filterable_protocol():
    assert isinstance(Os, Filterable)


@pytest.mark.parametrize("htmlcls", [HtmlString, KvRow])
def test_os_component_has_target_componenets(htmlcls):
    os = Os("ubunutu")
    assert isinstance(os.component(htmlcls), htmlcls)