from humitifier.models.package import Package
from .utils import gen_fake, FakeUtil
from itertools import cycle
from typing import Iterable


class FakePackage:
    name = FakeUtil.packagename
    version = FakeUtil.packageversion

    @classmethod
    def generate(cls, **kwargs) -> Package:
        return gen_fake(Package, cls, **kwargs)

    @staticmethod
    def create_pool() -> Iterable[Package]:
        packages = [FakePackage.generate() for _ in range(50)]
        for package in cycle(packages):
            yield package


PackagePool = FakePackage.create_pool()
