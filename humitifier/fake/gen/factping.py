from .utils import gen_fake, FakeUtil
from humitifier.models.factping import FactPing
from .facts import UserPool, FakeGroup, FakeHostnameCtl, FakeMemory, FakeBlock, FakeUptime, FakePackage


class FakeFactPing:
    users = lambda: [next(UserPool) for _ in range(FakeUtil.faker.pyint(min_value=5, max_value=20))]
    groups = lambda: [FakeGroup.generate() for _ in range(FakeUtil.faker.pyint(min_value=2, max_value=10))]
    hostnamectl = lambda: FakeHostnameCtl.generate()
    memory = lambda: FakeMemory.generate()
    block = lambda: [FakeBlock.generate() for _ in range(FakeUtil.faker.pyint(min_value=2, max_value=10))]
    uptime = lambda: FakeUptime.generate()
    packages = lambda: [FakePackage.generate() for _ in range(FakeUtil.faker.pyint(min_value=10, max_value=20))]

    @classmethod
    def generate(cls, **kwargs) -> FactPing:
        return gen_fake(FactPing, cls, **kwargs)
