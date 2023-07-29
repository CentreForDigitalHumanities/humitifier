import pytest
from humitifier.html import HtmlString, KvRow
from humitifier.facts import HostnameCtl
from humitifier.props import Virtualization
from humitifier.props.protocols import Property
from unittest.mock import patch

def test_virtualization_implements_prop_protocol():
    assert isinstance(Virtualization, Property)


def test_virtualization_from_host_state():
    with (
        patch("humitifier.props.virtualization.Virtualization._get_ctl") as mock_ctl):
        mock_ctl = HostnameCtl(
            hostname="host",
            os="CentOS Linux 8",
            kernel="4.18.0-193.28.1.el8_2.x86_64",
            cpe_os_name="cpe:/o:centos:centos:8",
            virtualization="kvm",
        )
        virtualization = Virtualization.from_host_state(mock_ctl)
        assert isinstance(virtualization, Virtualization)

@pytest.mark.parametrize("htmlcls", [HtmlString, KvRow])
def test_virtualization_component_has_target_componenets(htmlcls):
    virtualization = Virtualization("host")
    assert isinstance(virtualization.component(htmlcls), htmlcls)

