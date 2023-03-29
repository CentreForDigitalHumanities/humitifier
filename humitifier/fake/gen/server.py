from .utils import gen_fake, FakeUtil
from .package import PackagePool
from .servicecontract import FakeServiceContract
from humitifier.models.server import Server
from itertools import cycle
from typing import Iterable


class FakeServer:
    hostname = FakeUtil.hostname
    slug = FakeUtil.slug
    ip_address = FakeUtil.ipv4
    cpu_total = FakeUtil.cpu_cores
    memory_total = FakeUtil.memory_total
    memory_usage = FakeUtil.memory_usage
    local_storage_total = FakeUtil.local_storage_total
    is_virtual = lambda: FakeUtil.faker.pybool()
    os = FakeUtil.os
    uptime = lambda: FakeUtil.faker.time_delta()
    reboot_required = lambda: FakeUtil.faker.pybool()
    packages = lambda: [next(PackagePool) for _ in range(FakeUtil.faker.pyint(min_value=10, max_value=20))]
    service_contract = lambda: FakeServiceContract.generate()

    @classmethod
    def generate(cls, **kwargs) -> Server:
        return gen_fake(Server, cls, **kwargs)

    @staticmethod
    def create_pool() -> Iterable[Server]:
        servers = [FakeServer.generate() for _ in range(100)]
        for server in cycle(servers):
            yield server


ServerPool = FakeServer.create_pool()
