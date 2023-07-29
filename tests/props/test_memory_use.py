import pytest
from humitifier.facts.memory import Memory
from humitifier.html import HtmlString, KvRow, ProgressBar
from humitifier.props import MemoryUse
from humitifier.props.protocols import Property
from unittest.mock import patch


def test_memory_use_implements_prop_protocol():
    assert isinstance(MemoryUse, Property)


def test_memory_use_from_host_state():
    with patch("humitifier.props.memory_use.MemoryUse._get_memory") as mock_memory:
        mock_memory = Memory(
            total_mb=100,
            free_mb=50,
            used_mb=50,
            swap_free_mb=50,
            swap_total_mb=100,
            swap_used_mb=50,
        )
        memory_use = MemoryUse.from_host_state(mock_memory)
        assert isinstance(memory_use, MemoryUse)


@pytest.mark.parametrize("htmlcls", [HtmlString, KvRow, ProgressBar])
def test_memory_use_component_has_target_componenets(htmlcls):
    memory_use = MemoryUse(100, 50)
    assert isinstance(memory_use.component(htmlcls), htmlcls)