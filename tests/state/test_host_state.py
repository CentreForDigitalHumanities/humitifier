import pytest
from humitifier.config.host_view import HostViewConfig
from humitifier.state.host import HostState
from humitifier.props import Fqdn, Hostname
from humitifier.html import KvTable, HostCard, HostModal


def test_host_state_get_item():
    state = HostState(
        fqdn=Fqdn("test.example.com"),
        data={
            Hostname.alias: Hostname("test"),
        },
        view_cfg=HostViewConfig(
            card=[],
            table=[],
        )
    )
    assert state[Hostname] == Hostname("test")


@pytest.mark.parametrize("html_cls", [KvTable, HostCard, HostModal])
def test_host_state_component(html_cls):
    state = HostState(
        fqdn=Fqdn("test.example.com"),
        data={
            Hostname.alias: Hostname("test"),
        },
        view_cfg=HostViewConfig(
            card=[Hostname],
            table=[Hostname],
        )
    )
    assert isinstance(state.component(html_cls), html_cls)