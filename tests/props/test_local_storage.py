import pytest
from humitifier.html import HtmlString, KvRow, ProgressBar
from humitifier.props import LocalStorage
from humitifier.props.protocols import Property


def test_local_storage_implements_prop_protocol():
    assert isinstance(LocalStorage, Property)


@pytest.mark.parametrize("htmlcls", [HtmlString, KvRow, ProgressBar])
def test_local_storage_component_has_target_componenets(htmlcls):
    local_storage = LocalStorage("/", 100, 50)
    assert isinstance(local_storage.component(htmlcls), htmlcls)