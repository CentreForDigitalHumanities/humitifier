from humitifier.models.host import Host
from .utils import gen_fake, FakeUtil
from itertools import cycle
from typing import Iterable

from .person import PersonPool


class FakeMeta:
    department = FakeUtil.department
    owner = lambda: next(PersonPool)
    start_date = FakeUtil.start_date
    end_date = FakeUtil.end_date
    purpose = FakeUtil.purpose
    people = lambda: [next(PersonPool) for _ in range(FakeUtil.faker.random_int(0, 5))]

    @classmethod
    def generate(cls, **kwargs) -> dict:
        start = cls.start_date()
        return {
            "department": cls.department(),
            "owner": cls.owner().dict(),
            "start_date": start.isoformat(),
            "end_date": cls.end_date(start).isoformat(),
            "purpose": cls.purpose(),
            "people": [p.dict() for p in cls.people()]
        }


class FakeHost:
    fqdn = FakeUtil.fqdn
    metadata = lambda: FakeMeta.generate()

    @classmethod
    def generate(cls, **kwargs) -> Host:
        return gen_fake(Host, cls, **kwargs)
    
    @staticmethod
    def create_pool() -> Iterable[Host]:
        hosts = [FakeHost.generate() for _ in range(100)]
        for host in cycle(hosts):
            yield host

HostPool = FakeHost.create_pool()
