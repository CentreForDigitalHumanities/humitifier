from .utils import gen_fake, FakeUtil

from .person import PersonPool
from humitifier.models.servicecontract import ServiceContract


class FakeServiceContract:
    entity = FakeUtil.department
    owner = lambda: next(PersonPool)
    start_date = FakeUtil.start_date
    end_date = FakeUtil.end_date
    purpose = FakeUtil.purpose
    people = lambda: [next(PersonPool) for _ in range(FakeUtil.faker.random_int(0, 5))]

    @classmethod
    def generate(cls, **kwargs) -> ServiceContract:
        return gen_fake(ServiceContract, cls, **kwargs)
