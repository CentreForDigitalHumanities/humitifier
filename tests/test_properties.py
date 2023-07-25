import pytest
from humitifier.properties.metadata import (
    Department,
    Owner,
    StartDate,
    EndDate,
    RetireIn,
    Purpose,
    People,
)
from humitifier.properties.facts import (
    Hostname,
    Os,
    PackageList,
    Memory,
    LocalStorage,
    Virtualization,
    Uptime
)
from humitifier.fake.gen.facts import (
    FakeHostnameCtl,
    FakePackages,
    FakeMemory,
    FakeBlocks,
    FakeUptime,

)
from humitifier.fake.gen.host import FakeHost
from humitifier.fake.gen.host_state import FakeHostState


@pytest.mark.parametrize(
    "property_cls,key,value", [
        (Department, "department", "IT"),
        (Owner, "owner", {"name": "John Doe", "email": "jdoe@gmail.com", "notes": "waah"}),
        (StartDate, "start_date", "2021-01-01"),
        (EndDate, "end_date", "2021-01-01"),
        (RetireIn, "end_date", "2021-01-01"),
        (Purpose, "purpose", "testing"),
        (People, "people", [{"name": "John Doe", "email": "jdoe@gmail.com", "notes": "waah"}])
    ]
)
def test_builtin_metadata_props_can_be_accessed(property_cls, key, value):
    host = FakeHost.generate(metadata={key: value})
    host_state = FakeHostState.generate(host=host, facts={})
    property = property_cls.from_host_state(host_state)
    assert property.value
    assert property.kv_label
    assert property.render_kv_value()


@pytest.mark.parametrize(
    "property_cls,faker", [
        (Hostname, FakeHostnameCtl),
        (Os, FakeHostnameCtl),
        (PackageList, FakePackages),
        (Memory, FakeMemory),
        (LocalStorage, FakeBlocks),
        (Virtualization, FakeHostnameCtl),
        (Uptime, FakeUptime)
    ])
def test_builtin_fact_props_can_be_accessed(property_cls, faker):
    fact = faker.generate()
    host_state = FakeHostState.generate(facts={fact.alias: fact})
    property = property_cls.from_host_state(host_state)
    assert property.value is not None
    assert property.kv_label
    assert property.render_kv_value()