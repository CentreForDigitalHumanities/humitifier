import pytest
from humitifier.html import HtmlString, KvRow
from humitifier.props import Purpose
from humitifier.props.protocols import Property
from unittest.mock import patch


def test_purpose_implements_prop_protocol():
    assert isinstance(Purpose, Property)


def test_purpose_from_host_state():
    with patch("humitifier.props.purpose.HostState") as mock_host_state:
        mock_host_state.metadata = {"purpose": "engineering"}
        purpose = Purpose.from_host_state(mock_host_state)
        assert isinstance(purpose, Purpose)
        assert purpose == "engineering"


@pytest.mark.parametrize("htmlcls", [HtmlString, KvRow])
def test_purpose_component_has_target_componenets(htmlcls):
    purpose = Purpose("engineering")
    assert isinstance(purpose.component(htmlcls), htmlcls)