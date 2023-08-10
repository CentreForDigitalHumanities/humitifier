import pytest
from humitifier.html import HtmlString, KvRow
from humitifier.props import EndDate
from humitifier.props.protocols import Property


def test_end_date_implements_prop_protocol():
    assert isinstance(EndDate, Property)


@pytest.mark.parametrize("htmlcls", [HtmlString, KvRow])
def test_end_date_component_has_target_componenets(htmlcls):
    end_date = EndDate(2020, 1, 1)
    assert isinstance(end_date.component(htmlcls), htmlcls)