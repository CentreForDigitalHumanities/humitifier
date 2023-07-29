import pytest
from humitifier.html import MailTo, KvRow
from humitifier.props import Owner
from humitifier.props.protocols import Property
from unittest.mock import patch


def test_owner_implements_prop_protocol():
    assert isinstance(Owner, Property)


def test_owner_from_host_state():
    with patch("humitifier.props.owner.HostState") as mock_host_state:
        mock_host_state.metadata = {"owner": {
            "name": "hagrid",
            "email": "lalala",
            "notes": "wahahah"
        }}
        owner = Owner.from_host_state(mock_host_state)
        assert isinstance(owner, Owner)

@pytest.mark.parametrize("htmlcls", [MailTo, KvRow])
def test_owner_component_has_target_componenets(htmlcls):
    owner = Owner("hagrid", "lalala", "wahahah")
    assert isinstance(owner.component(htmlcls), htmlcls)