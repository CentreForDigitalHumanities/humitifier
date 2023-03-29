from typing import Type, TypeVar
from pydantic import BaseModel
from faker import Faker
from datetime import date
from humitifier.fake import lists

T = TypeVar("T", bound=BaseModel)
F = TypeVar("F")
Fake = Faker()


def gen_fake(target_cls: Type[T], fake_cls: Type[F], **kwargs) -> T:
    to_generate = (k for k in target_cls.__annotations__.keys() if k not in kwargs)
    for k in to_generate:
        func = getattr(fake_cls, k)
        required = func.__annotations__.keys()
        func_kwargs = {k: kwargs[k] for k in required}
        kwargs[k] = func(**func_kwargs)
    return target_cls(**kwargs)


class FakeUtil:
    faker = Fake

    @staticmethod
    def fullname():
        first_name = Fake.random_element(elements=lists.first_names)
        last_name = Fake.random_element(elements=lists.last_names)
        return f"{first_name} {last_name}"

    @staticmethod
    def email(name: str):
        first_name, _, last_name = name.partition(" ")
        username = f"{first_name[0]}.{last_name}".lower()
        domain = Fake.random_element(elements=lists.domains)
        return f"{username}@{domain}"

    @staticmethod
    def packagename():
        return Fake.random_element(elements=lists.packages)

    @staticmethod
    def packageversion():
        return Fake.pystr_format(string_format="##.##.##")

    @staticmethod
    def department():
        return Fake.random_element(elements=lists.departments)

    @staticmethod
    def start_date():
        return Fake.date_between(start_date="-1y", end_date="today")

    @staticmethod
    def end_date(start_date: date):
        return Fake.date_between(start_date=start_date, end_date="+1y")

    @staticmethod
    def purpose():
        return Fake.random_element(elements=lists.applications)

    @staticmethod
    def hostname():
        return Fake.hostname()

    @staticmethod
    def slug(hostname: str):
        return f"{hostname}.{Fake.random_element(elements=lists.domains)}"

    @staticmethod
    def ipv4():
        return Fake.ipv4()

    @staticmethod
    def cpu_cores():
        return Fake.pyint(min_value=1, max_value=8)

    @staticmethod
    def memory_total():
        return Fake.pyfloat(min_value=2, max_value=16)

    @staticmethod
    def memory_usage(memory_total: float):
        return Fake.pyfloat(min_value=0, max_value=memory_total)

    @staticmethod
    def local_storage_total():
        return Fake.pyfloat(min_value=20, max_value=100)

    @staticmethod
    def os():
        return Fake.random_element(elements=lists.operating_systems)

    @staticmethod
    def clustername():
        return Fake.random_element(elements=lists.packages)
