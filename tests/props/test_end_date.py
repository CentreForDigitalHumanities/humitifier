import pytest
from datetime import date
from humitifier.html import HtmlString, KvRow
from humitifier.props import EndDate
from humitifier.props.protocols import Property
from unittest.mock import patch


def test_end_date_implements_prop_protocol():
    assert isinstance(EndDate, Property)


def test_end_date_from_host_state():
    with patch("humitifier.props.end_date.HostState") as mock_host_state:
        mock_host_state.metadata = {"end_date": "2020-01-01"}
        end_date = EndDate.from_host_state(mock_host_state)
        assert isinstance(end_date, EndDate)
        assert end_date == date(2020, 1, 1)


@pytest.mark.parametrize("htmlcls", [HtmlString, KvRow])
def test_end_date_component_has_target_componenets(htmlcls):
    end_date = EndDate(2020, 1, 1)
    assert isinstance(end_date.component(htmlcls), htmlcls)