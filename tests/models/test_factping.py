from humitifier.fake.gen import facts as fake_facts
from humitifier.models.factping import FactPing


def test_fact_ping_from_facts():
    facts = [
        fake_facts.FakeHostnameCtl.generate(),
        fake_facts.FakeMemory.generate(),
        fake_facts.FakeUptime.generate(),
        [fake_facts.FakeUser.generate() for _ in range(5)],
        [fake_facts.FakeGroup.generate() for _ in range(5)],
        [fake_facts.FakeBlock.generate() for _ in range(5)],
        [fake_facts.FakePackage.generate() for _ in range(5)],
    ]
    fact_ping = FactPing.from_facts(facts)
    assert fact_ping.hostnamectl
    assert fact_ping.memory
    assert fact_ping.uptime
    assert fact_ping.users
    assert fact_ping.groups
    assert fact_ping.blocks
    assert fact_ping.packages
