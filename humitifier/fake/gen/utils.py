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
    def firstname():
        return Fake.random_element(elements=lists.first_names)

    @staticmethod
    def lastname():
        return Fake.random_element(elements=lists.last_names)

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

    @staticmethod
    def kernel():
        return Fake.random_element(elements=lists.kernels)

    @staticmethod
    def total_mb():
        return Fake.pyint(min_value=1024, max_value=16384)

    @staticmethod
    def used_mb(total_mb: int):
        return Fake.pyint(min_value=0, max_value=total_mb)

    @staticmethod
    def free_mb(total_mb: int, used_mb: int):
        return Fake.pyint(min_value=0, max_value=total_mb - used_mb)

    @staticmethod
    def swap_total_mb():
        return Fake.pyint(min_value=1024, max_value=16384)

    @staticmethod
    def swap_used_mb(swap_total_mb: int):
        return Fake.pyint(min_value=0, max_value=swap_total_mb)

    @staticmethod
    def swap_free_mb(swap_total_mb: int, swap_used_mb: int):
        return Fake.pyint(min_value=0, max_value=swap_total_mb - swap_used_mb)

    @staticmethod
    def blockname():
        return Fake.random_element(elements=lists.block_devices)

    @staticmethod
    def blocksize():
        return Fake.pyint(min_value=1024, max_value=16384)

    @staticmethod
    def blockused(size_mb: int):
        return Fake.pyint(min_value=0, max_value=size_mb)

    @staticmethod
    def blockfree(size_mb: int, used_mb: int):
        return Fake.pyint(min_value=0, max_value=size_mb - used_mb)

    @staticmethod
    def blockmountpoint():
        return Fake.random_element(elements=lists.mountpoints)

    @staticmethod
    def blockpercent():
        return Fake.pyfloat(min_value=0, max_value=100)

    @staticmethod
    def groupname():
        return Fake.random_element(elements=lists.user_groups)

    @staticmethod
    def gid():
        return Fake.pyint(min_value=1000, max_value=60000)

    @staticmethod
    def username():
        return Fake.random_element(elements=lists.first_names).lower()

    @staticmethod
    def uid():
        return Fake.pyint(min_value=1000, max_value=60000)

    @staticmethod
    def userhome(name: str):
        return f"/home/{name}"

    @staticmethod
    def usershell():
        return Fake.random_element(elements=lists.shells)

    @staticmethod
    def userinfo(name: str):
        return f"{name} {FakeUtil.email(name + ' ' + FakeUtil.lastname())}"
