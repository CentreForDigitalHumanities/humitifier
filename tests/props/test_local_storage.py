import pytest
from humitifier.facts.blocks import Block
from humitifier.html import HtmlString, KvRow, ProgressBar
from humitifier.props import LocalStorage
from humitifier.props.protocols import Property
from unittest.mock import patch


def test_local_storage_implements_prop_protocol():
    assert isinstance(LocalStorage, Property)


def test_local_storage_from_host_state():
    with patch("humitifier.props.local_storage.LocalStorage._get_blocks") as mock_blocks:
        mock_blocks = [Block(
            name="local_storage",
            available_mb=100,
            used_mb=50,
            mount="/",
            use_percent=50,
            size_mb=100,
        )]
        local_storage = LocalStorage.from_host_state(mock_blocks)
        assert isinstance(local_storage, LocalStorage)


@pytest.mark.parametrize("htmlcls", [HtmlString, KvRow, ProgressBar])
def test_local_storage_component_has_target_componenets(htmlcls):
    local_storage = LocalStorage("/", 100, 50)
    assert isinstance(local_storage.component(htmlcls), htmlcls)