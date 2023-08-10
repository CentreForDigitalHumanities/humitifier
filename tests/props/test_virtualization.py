import pytest
from humitifier.html import HtmlString, KvRow
from humitifier.props import Virtualization
from humitifier.props.protocols import Property
from unittest.mock import patch

def test_virtualization_implements_prop_protocol():
    assert isinstance(Virtualization, Property)


@pytest.mark.parametrize("htmlcls", [HtmlString, KvRow])
def test_virtualization_component_has_target_componenets(htmlcls):
    virtualization = Virtualization("host")
    assert isinstance(virtualization.component(htmlcls), htmlcls)

