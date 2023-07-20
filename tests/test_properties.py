import pytest
from humitifier.properties import MetadataProperty, FactProperty, PropertyReadError
from humitifier.fake.gen.host_state import FakeHostState


@pytest.mark.parametrize("prop", list(MetadataProperty))
def test_metadata_properties_extract(prop):
    state = FakeHostState.generate()
    assert prop.extract(state) is not None


def test_metadata_extract_raises_error_on_invalid_property():
    state = FakeHostState.generate()
    state.host.metadata = {}
    with pytest.raises(PropertyReadError):
        MetadataProperty.Department.extract(state)


@pytest.mark.parametrize("prop", list(FactProperty))
def test_fact_properties_extract(prop):
    state = FakeHostState.generate()
    assert prop.extract(state) is not None


def test_fact_extract_raises_error_on_invalid_property():
    state = FakeHostState.generate()
    state.facts.hostnamectl = None
    with pytest.raises(PropertyReadError):
        FactProperty.Hostname.extract(state)