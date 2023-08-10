from faker import Faker
from . import lists

Fake = Faker()

def firstname():
    return Fake.random_element(elements=lists.first_names)

def lastname():
    return Fake.random_element(elements=lists.last_names)

def fullname(first=None, last=None):
    return f"{first or firstname()} {last or lastname()}"

def username(first=None, last=None):
    first_name = first or firstname()
    last_name = last or lastname()
    return f"{first_name[0]}.{last_name}".lower()

def email(user=None):
    user = user or username()
    domain = Fake.random_element(elements=lists.domains)
    return f"{user}@{domain}"

def packagename():
    return Fake.random_element(elements=lists.packages)

def packageversion():
    return Fake.pystr_format(string_format="##.##.##")

def department():
    return Fake.random_element(elements=lists.departments)

def start_date():
    return Fake.date_between(start_date="-1y", end_date="today")

def end_date(start=None):
    start = start or start_date()
    return Fake.date_between(start_date=start, end_date="+1y")

def purpose():
    return Fake.random_element(elements=lists.applications)

def hostname(purp=None, dept=None):
    dept = dept or department()
    return f"{dept[0:3]}-{purp or purpose()}"

def ipv4():
    return Fake.ipv4()

def total_mb(min=1, max=64):
    return Fake.random_int(min=min, max=max) * 1024

def used_mb(min=1, max=None):
    max = max or total_mb()
    return Fake.random_int(min=min, max=max)

def free_mb(total=None, used=None):
    total = total or total_mb()
    used = used or used_mb(total)
    return total - used

def blockname():
    return Fake.random_element(elements=lists.block_devices)

def mountpoint():
    return Fake.random_element(elements=lists.mountpoints)

def kernel():
    return Fake.random_element(elements=lists.kernels)

def usergroup():
    return Fake.random_element(elements=lists.user_groups)

def operating_system():
    return Fake.random_element(elements=lists.operating_systems)

def groupname():
    return Fake.random_element(elements=lists.user_groups)

def gid():
    return Fake.random_int(min=1000, max=9999)

def uid():
    return Fake.random_int(min=1000, max=9999)

def userhome(user=None):
    user = user or username()
    return f"/home/{user}"

def shell():
    return Fake.random_element(elements=lists.shells)

def fqdn(host=None):
    return f"{host or hostname()}.{Fake.random_element(elements=lists.domains)}"

def package():
    return Fake.random_element(elements=lists.packages)

def version():
    return Fake.pystr_format(string_format="##.##.##")