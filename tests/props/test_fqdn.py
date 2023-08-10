import pytest
from humitifier.html import HtmlString, KvRow
from humitifier.props import Fqdn
from humitifier.props.protocols import Property

def test_fqdn_implements_prop_protocol():
    assert isinstance(Fqdn, Property)


@pytest.mark.parametrize("htmlcls", [HtmlString, KvRow])
def test_fqdn_component_has_target_componenets(htmlcls):
    fqdn = Fqdn("host.example.com")
    assert isinstance(fqdn.component(htmlcls), htmlcls)