from .utils import gen_fake, FakeUtil
from .server import ServerPool
from humitifier.models.cluster import Cluster


class FakeCluster:
    name = FakeUtil.clustername
    servers = lambda: [next(ServerPool) for _ in range(FakeUtil.faker.random_int(10, 50))]

    @classmethod
    def generate(cls, **kwargs) -> Cluster:
        return gen_fake(Cluster, cls, **kwargs)
