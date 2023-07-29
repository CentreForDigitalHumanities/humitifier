import pytest
from datetime import date
from humitifier.html import HtmlString, KvRow
from humitifier.props import StartDate
from humitifier.props.protocols import Property
from unittest.mock import patch


def test_start_date_implements_prop_protocol():
    assert isinstance(StartDate, Property)


def test_start_date_from_host_state():
    with patch("humitifier.props.end_date.HostState") as mock_host_state:
        mock_host_state.metadata = {"start_date": "2020-01-01"}
        start_date = StartDate.from_host_state(mock_host_state)
        assert isinstance(start_date, StartDate)
        assert start_date == date(2020, 1, 1)


@pytest.mark.parametrize("htmlcls", [HtmlString, KvRow])
def test_start_date_component_has_target_componenets(htmlcls):
    start_date = StartDate(2020, 1, 1)
    assert isinstance(start_date.component(htmlcls), htmlcls)