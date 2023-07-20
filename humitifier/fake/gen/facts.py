from .utils import gen_fake, FakeUtil
from humitifier import facts as infra_facts
from typing import Iterable
from itertools import cycle


class FakeHostnameCtl:
    hostname: str = FakeUtil.hostname
    kernel: str = FakeUtil.kernel
    os: str = FakeUtil.os
    cpe_os_name: str = FakeUtil.os
    virtualization: str | None = lambda: FakeUtil.faker.random_element(elements=["vmware", None])

    @classmethod
    def generate(cls, **kwargs) -> infra_facts.HostnameCtl:
        return gen_fake(infra_facts.HostnameCtl, cls, **kwargs)

    @staticmethod
    def create_pool() -> Iterable[infra_facts.HostnameCtl]:
        ctls = [FakeHostnameCtl.generate() for _ in range(4)]
        for ctl in cycle(ctls):
            yield ctl


class FakePackage:
    name = FakeUtil.packagename
    version = FakeUtil.packageversion

    @classmethod
    def generate(cls, **kwargs) -> infra_facts.Package:
        return gen_fake(infra_facts.Package, cls, **kwargs)

    @staticmethod
    def create_pool() -> Iterable[infra_facts.Package]:
        packages = [FakePackage.generate() for _ in range(50)]
        for package in cycle(packages):
            yield package


class FakeMemory:
    total_mb: int = FakeUtil.total_mb
    used_mb: int = FakeUtil.used_mb
    free_mb: int = FakeUtil.free_mb
    swap_total_mb: int = FakeUtil.swap_total_mb
    swap_used_mb: int = FakeUtil.swap_used_mb
    swap_free_mb: int = FakeUtil.swap_free_mb

    @classmethod
    def generate(cls, **kwargs) -> infra_facts.Memory:
        return gen_fake(infra_facts.Memory, cls, **kwargs)


class FakeBlock:
    name: str = FakeUtil.blockname
    size_mb: int = FakeUtil.blocksize
    used_mb: int = FakeUtil.blockused
    available_mb: int = FakeUtil.blockfree
    use_percent: int = FakeUtil.blockpercent
    mount: str = FakeUtil.blockmountpoint

    @classmethod
    def generate(cls, **kwargs) -> infra_facts.Block:
        return gen_fake(infra_facts.Block, cls, **kwargs)


class FakeUptime:
    @classmethod
    def generate(cls, **kwargs) -> infra_facts.Uptime:
        delta = FakeUtil.faker.time_delta(end_datetime=FakeUtil.faker.future_date("+1y"))
        return infra_facts.Uptime(seconds=delta.total_seconds())


class FakeGroup:
    name: str = FakeUtil.groupname
    gid: int = FakeUtil.gid
    users: list[str] = lambda: [FakeUtil.username() for _ in range(FakeUtil.faker.pyint(min_value=1, max_value=10))]

    @classmethod
    def generate(cls, **kwargs) -> infra_facts.Group:
        return gen_fake(infra_facts.Group, cls, **kwargs)


class FakeUser:
    name: str = FakeUtil.username
    uid: int = FakeUtil.uid
    gid: int = FakeUtil.gid
    home: str = FakeUtil.userhome
    info: str = FakeUtil.userinfo
    shell: str = FakeUtil.usershell

    @classmethod
    def generate(cls, **kwargs) -> infra_facts.User:
        return gen_fake(infra_facts.User, cls, **kwargs)

    @classmethod
    def create_pool(cls) -> Iterable[infra_facts.User]:
        users = [FakeUser.generate() for _ in range(50)]
        for user in cycle(users):
            yield user


HostnameCtlPool = FakeHostnameCtl.create_pool()
PackagePool = FakePackage.create_pool()
UserPool = FakeUser.create_pool()
