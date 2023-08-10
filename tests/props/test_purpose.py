import pytest
from humitifier.html import HtmlString, KvRow
from humitifier.props import Purpose
from humitifier.props.protocols import Property, Filterable


def test_purpose_implements_prop_protocol():
    assert isinstance(Purpose, Property)


def test_purpose_implements_filterable_protocol():
    assert isinstance(Purpose, Filterable)



@pytest.mark.parametrize("htmlcls", [HtmlString, KvRow])
def test_purpose_component_has_target_componenets(htmlcls):
    purpose = Purpose("engineering")
    assert isinstance(purpose.component(htmlcls), htmlcls)