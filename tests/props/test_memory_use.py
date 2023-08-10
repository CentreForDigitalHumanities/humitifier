import pytest
from humitifier.html import HtmlString, KvRow, ProgressBar
from humitifier.props import MemoryUse
from humitifier.props.protocols import Property


def test_memory_use_implements_prop_protocol():
    assert isinstance(MemoryUse, Property)


@pytest.mark.parametrize("htmlcls", [HtmlString, KvRow, ProgressBar])
def test_memory_use_component_has_target_componenets(htmlcls):
    memory_use = MemoryUse(100, 50)
    assert isinstance(memory_use.component(htmlcls), htmlcls)