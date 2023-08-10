import pytest
from datetime import date
from humitifier.html import HtmlString, KvRow
from humitifier.props import StartDate
from humitifier.props.protocols import Property
from unittest.mock import patch


def test_start_date_implements_prop_protocol():
    assert isinstance(StartDate, Property)


@pytest.mark.parametrize("htmlcls", [HtmlString, KvRow])
def test_start_date_component_has_target_componenets(htmlcls):
    start_date = StartDate(2020, 1, 1)
    assert isinstance(start_date.component(htmlcls), htmlcls)