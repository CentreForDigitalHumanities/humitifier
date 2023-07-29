import pytest
from humitifier.html import HtmlString, KvRow
from humitifier.props import Fqdn
from humitifier.props.protocols import Property
from unittest.mock import patch

def test_fqdn_implements_prop_protocol():
    assert isinstance(Fqdn, Property)


def test_fqdn_from_host_state():
    with patch("humitifier.props.fqdn.HostState") as mock_host_state:
        mock_host_state.host.fqdn = "host.example.com"
        fqdn = Fqdn.from_host_state(mock_host_state)
        assert isinstance(fqdn, Fqdn)
        assert fqdn == "host.example.com"


@pytest.mark.parametrize("htmlcls", [HtmlString, KvRow])
def test_fqdn_component_has_target_componenets(htmlcls):
    fqdn = Fqdn("host.example.com")
    assert isinstance(fqdn.component(htmlcls), htmlcls)