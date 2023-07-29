import pytest
from humitifier.facts.hostnamectl import HostnameCtl
from humitifier.html import HtmlString, KvRow
from humitifier.props import Os
from humitifier.props.protocols import Property, Filterable
from unittest.mock import patch


def test_os_implements_prop_protocol():
    assert isinstance(Os, Property)


def test_os_implements_filterable_protocol():
    assert isinstance(Os, Filterable)


def test_os_from_host_state():
    with (
        patch("humitifier.props.os.Os._get_ctl") as mock_ctl):
        mock_ctl = HostnameCtl(
            hostname="host",
            os="CentOS Linux 8",
            kernel="4.18.0-193.28.1.el8_2.x86_64",
            cpe_os_name="cpe:/o:centos:centos:8",
            virtualization="kvm",
        )
        os = Os.from_host_state(mock_ctl)
        assert isinstance(os, Os)


@pytest.mark.parametrize("htmlcls", [HtmlString, KvRow])
def test_os_component_has_target_componenets(htmlcls):
    os = Os("ubunutu")
    assert isinstance(os.component(htmlcls), htmlcls)