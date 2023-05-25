from .utils import gen_fake
from .servicecontract import FakeServiceContract
from .factping import FakeFactPing
from humitifier.models.server import Server
from itertools import cycle
from typing import Iterable


class FakeServer:
    facts = lambda: FakeFactPing.generate()
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
