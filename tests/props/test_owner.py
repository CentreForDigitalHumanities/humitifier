import pytest
from humitifier.html import MailTo, KvRow
from humitifier.props import Owner
from humitifier.props.protocols import Property, Filterable


def test_owner_implements_prop_protocol():
    assert isinstance(Owner, Property)


def test_owner_implements_filterable_protocol():
    assert isinstance(Owner, Filterable)


@pytest.mark.parametrize("htmlcls", [MailTo, KvRow])
def test_owner_component_has_target_componenets(htmlcls):
    owner = Owner("hagrid", "lalala", "wahahah")
    assert isinstance(owner.component(htmlcls), htmlcls)