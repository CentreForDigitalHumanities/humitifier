import pytest
from humitifier.fake.gen.facts import FakePackage
from humitifier.fake.gen.host_state import FakeHostState
from humitifier.filters import Filter

@pytest.mark.parametrize("filter", list(Filter))
def test_filter_extract_values(filter):
    state = FakeHostState.generate()
    assert filter.extract_value(state)


@pytest.mark.parametrize("filter", list(Filter))
def test_filter_options(filter):
    states = [FakeHostState.generate() for _ in range(10)]
    assert filter.options(states)
    assert all(isinstance(o, str) for o in filter.options(states))

def test_filter_on_hostname():
    state = FakeHostState.generate()
    state.facts.hostnamectl.hostname = "foo"
    assert Filter.Hostname.apply(state, "foo")
    assert not Filter.Hostname.apply(state, "bar")
    assert Filter.Hostname.apply(state, "fo")

def test_filter_on_os():
    state = FakeHostState.generate()
    state.facts.hostnamectl.os = "foo"
    assert Filter.Os.apply(state, "foo")
    assert not Filter.Os.apply(state, "bar")
    assert not Filter.Os.apply(state, "fo")

def test_filter_on_package():
    state = FakeHostState.generate()
    state.facts.packages = [FakePackage.generate(name="waah"), FakePackage.generate(name="foo")]
    assert Filter.Package.apply(state, "foo")
    assert Filter.Package.apply(state, "waah")
    assert Filter.Package.apply(state, "wa")
    assert not Filter.Package.apply(state, "bar")

def test_filter_on_department():
    state = FakeHostState.generate()
    state.host.metadata["department"] = "foo"
    assert Filter.Department.apply(state, "foo")
    assert not Filter.Department.apply(state, "bar")
    assert not Filter.Department.apply(state, "fo")

def test_filter_on_owner():
    state = FakeHostState.generate()
    state.host.metadata["owner"] = {"name": "foo", "email": "lalala", "notes": "wah"}
    assert Filter.Owner.apply(state, "foo")
    assert not Filter.Owner.apply(state, "bar")
    assert Filter.Owner.apply(state, "fo")

def test_filter_on_purpose():
    state = FakeHostState.generate()
    state.host.metadata["purpose"] = "foo"
    assert Filter.Purpose.apply(state, "foo")
    assert not Filter.Purpose.apply(state, "bar")
    assert not Filter.Purpose.apply(state, "fo")

def test_filter_on_person():
    state = FakeHostState.generate()
    state.host.metadata["people"] = [
        {"name": "foo", "email": "lalala", "notes": "wah"},
        {"name": "bar", "email": "lalala", "notes": "wah"},
    ]
    assert Filter.Person.apply(state, "foo")
    assert Filter.Person.apply(state, "bar")
    assert Filter.Person.apply(state, "fo")
    assert not Filter.Person.apply(state, "wah")

@pytest.mark.parametrize("filter", list(Filter))
def test_cann_apply_all_filters(filter):
    state = FakeHostState.generate()
    filter.apply(state, "foo")