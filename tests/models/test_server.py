from humitifier.models.server import Server
from humitifier.fake.gen.servicecontract import FakeServiceContract
from humitifier.fake.gen.package import PackagePool


example_boltdata = {
    "target": "example-server",
    "value": {
        "hostname": "example.com",
        "ipaddress": "192.168.1.100",
        "processorcount": 4,
        "memorysize_mb": 8192,
        "memoryfree_mb": 2048,
        "blockdevice_sda_size": 50000000000,
        "is_virtual": True,
        "operatingsystem": "Ubuntu",
        "operatingsystemrelease": "18.04.1",
        "uptime_seconds": 86400,
    },
}


def test_server_extract_bolt_kwargs():
    kwargs = Server.extract_bolt_kwargs(example_boltdata)
    assert kwargs["slug"]


def test_load_server_from_bolt():
    packages = [next(PackagePool) for _ in range(20)]
    contract = FakeServiceContract.generate()
    kwargs = Server.extract_bolt_kwargs(example_boltdata)
    server = Server.create(servicecontract=contract, packages=packages, **kwargs)
    assert server.slug


def test_load_servers_from_files():
    servers = Server.load("tests/models/fixtures/boltscan.json", "tests/models/fixtures/")
    assert len(servers) == 1
    assert servers[0].slug == "example-server"
    assert len(servers[0].packages) == 2


def test_load_servers_from_files_without_servicecontract():
    servers = Server.load("tests/models/fixtures/boltscan.json", "tests/models/")
    assert len(servers) == 1
    assert servers[0].slug == "example-server"
    assert len(servers[0].packages) == 2
    assert servers[0].service_contract is None
