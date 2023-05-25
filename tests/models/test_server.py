from humitifier.models.server import Server
from humitifier.fake.gen.factping import FakeFactPing
from humitifier.fake.gen.servicecontract import FakeServiceContract


def test_server_properties():
    facts = FakeFactPing.generate()
    service_contract = FakeServiceContract.generate()
    server = Server(facts=facts, service_contract=service_contract)
    assert server.hostname
    assert server.memory_total
    assert server.memory_usage
    assert server.local_storage_total
    assert server.is_virtual is not None
    assert server.os
    assert server.uptime_days
    assert server.packages
