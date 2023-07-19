from humitifier.models.person import Person
from .utils import gen_fake, FakeUtil
from itertools import cycle
from typing import Iterable


class FakePerson:
    name = FakeUtil.fullname
    email = FakeUtil.email
    notes = FakeUtil.groupname

    @classmethod
    def generate(cls, **kwargs) -> Person:
        return gen_fake(Person, cls, **kwargs)

    @staticmethod
    def create_pool() -> Iterable[Person]:
        people = [FakePerson.generate() for _ in range(100)]
        for person in cycle(people):
            yield person


PersonPool = FakePerson.create_pool()
