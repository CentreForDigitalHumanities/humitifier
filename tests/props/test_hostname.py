import pytest
from humitifier.html import HtmlString, KvRow
from humitifier.props import Hostname
from humitifier.props.protocols import Property, Filterable

def test_hostname_implements_prop_protocol():
    assert isinstance(Hostname, Property)

def test_hostname_implements_filterable_protocol():
    assert isinstance(Hostname, Filterable)


@pytest.mark.parametrize("htmlcls", [HtmlString, KvRow])
def test_hostname_component_has_target_componenets(htmlcls):
    hostname = Hostname("host")
    assert isinstance(hostname.component(htmlcls), htmlcls)

