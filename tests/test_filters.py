import pytest
from humitifier.fake.gen.facts import FakePackages, FakePackage
from humitifier.fake.gen.host_state import FakeHostState
from humitifier.filters import (
    HostnameFilter,
    OsFilter,
    PackageFilter,
    DepartmentFilter,
    OwnerFilter,
    PurposeFilter,
    PersonFilter,
    filter_options
)

def test_hostname_filter_apply():
    host_state = FakeHostState.generate()
    host_state.facts["hostnamectl"].hostname = "foo"
    assert HostnameFilter.apply(host_state, "foo")
    assert HostnameFilter.apply(host_state, "fo")
    assert not HostnameFilter.apply(host_state, "x")


def test_os_filter_apply():
    host_state = FakeHostState.generate()
    host_state.facts["hostnamectl"].os = "foo"
    assert OsFilter.apply(host_state, "foo")
    assert not OsFilter.apply(host_state, "fo")
    assert not OsFilter.apply(host_state, "x")

def test_package_filter_apply():
    host_state = FakeHostState.generate()
    packages = FakePackages.generate()
    packages.items = [FakePackage.generate(name="foo")]
    host_state.facts["packages"] = packages
    assert PackageFilter.apply(host_state, "foo")
    assert PackageFilter.apply(host_state, "fo")
    assert not PackageFilter.apply(host_state, "x")

def test_department_filter_apply():
    host_state = FakeHostState.generate()
    host_state.host.metadata["department"] = "foo"
    assert DepartmentFilter.apply(host_state, "foo")
    assert not DepartmentFilter.apply(host_state, "fo")
    assert not DepartmentFilter.apply(host_state, "x")

def test_owner_filter_apply():
    host_state = FakeHostState.generate()
    host_state.host.metadata["owner"] = {"name": "foo", "email": "woo", "notes": "bar"}
    assert OwnerFilter.apply(host_state, "foo")
    assert OwnerFilter.apply(host_state, "fo")
    assert not OwnerFilter.apply(host_state, "x")

def test_purpose_filter_apply():
    host_state = FakeHostState.generate()
    host_state.host.metadata["purpose"] = "foo"
    assert PurposeFilter.apply(host_state, "foo")
    assert not PurposeFilter.apply(host_state, "fo")
    assert not PurposeFilter.apply(host_state, "x")

def test_person_filter_apply():
    host_state = FakeHostState.generate()
    host_state.host.metadata["people"] = [{"name": "foo", "email": "woo", "notes": "bar"}]
    assert PersonFilter.apply(host_state, "foo")
    assert PersonFilter.apply(host_state, "fo")
    assert not PersonFilter.apply(host_state, "x")

@pytest.mark.parametrize("filter_cls", [
    HostnameFilter, 
    OsFilter, 
    PackageFilter, 
    DepartmentFilter, 
    OwnerFilter, 
    PurposeFilter, 
    PersonFilter
])
def test_filter_options_are_generated(filter_cls):
    host_states = [FakeHostState.generate() for _ in range(3)]
    options = filter_options(filter_cls.options(host_states))
    assert isinstance(options, list)
    assert all(isinstance(o, str) for o in options)