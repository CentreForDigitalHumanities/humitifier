from faker import Faker
from datetime import date, timedelta
from humitifier.fake import lists
from humitifier.fake.helpers import unique_list_picks, generate_full_name, generate_email, generate_username
from humitifier.models import Server, Person, ServiceContract, Package
from typing import Optional, Literal

fake = Faker()


def generate_person(
    name: Optional[str] = None,
    email: Optional[str] = None,
    role: Optional[Literal["admin", "user", "developer", "researcher"]] = None,
    department: Optional[str] = None,
    notes: Optional[str] = None,
) -> Person:
    if not name:
        name = generate_full_name()
    if not email:
        email = generate_email(generate_username(name))
    if not role:
        role = fake.random_element(elements=("admin", "user", "developer", "researcher"))
    if not department:
        department = fake.random_element(elements=lists.departments)
    if not notes:
        notes = fake.text()
    return Person(name=name, email=email, role=role, department=department, notes=notes)


def generate_service_contract(
    entity: Optional[str] = None,
    owner: Optional[Person] = None,
    creation_date: Optional[date] = None,
    expiry_date: Optional[date] = None,
    purpose: Optional[str] = None,
) -> ServiceContract:
    if entity is None:
        entity = fake.random_element(elements=lists.departments)
    if owner is None:
        owner = generate_person()
    if creation_date is None:
        creation_date = fake.date_between(start_date="-1y", end_date="today")
    if expiry_date is None:
        expiry_date = fake.date_between(start_date=creation_date, end_date="+1y")
    if purpose is None:
        purpose = fake.random_element(elements=lists.applications)
    return ServiceContract(
        entity=entity, owner=owner, creation_date=creation_date, expiry_date=expiry_date, purpose=purpose
    )


def generate_package(name: Optional[str] = None, version: Optional[str] = None) -> Package:
    if name is None:
        name = fake.random_element(elements=lists.packages)
    if version is None:
        version = f"{fake.random_int(min=1, max=10)}.{fake.random_int(min=1, max=10)}.{fake.random_int(min=1, max=10)}-{fake.word()}{fake.random_int(min=1, max=10)}{fake.word()}"
    return Package(name=name, version=version)


def generate_server(
    name: str = None,
    ip_address: str = None,
    cpu_total: int = None,
    cpu_usage: float = None,
    memory_total: int = None,
    memory_usage: int = None,
    local_storage_total: int = None,
    local_storage_usage: int = None,
    is_virtual: bool = None,
    os: str = None,
    uptime: timedelta = None,
    nfs_shares: list[str] = None,
    webdav_shares: list[str] = None,
    packages: list[Package] = None,
    service_contract: ServiceContract = None,
    people: list[Person] = None,
    reboot_required: bool = None,
    users: list[str] = None,
    groups: list[str] = None,
) -> Server:
    if not name:
        name = fake.hostname()
    if not ip_address:
        ip_address = fake.ipv4()
    if not cpu_total:
        cpu_total = fake.random_int(min=1, max=64)
    if not cpu_usage:
        cpu_usage = fake.random_int(min=0, max=100) * 1.0
    if not memory_total:
        memory_total = fake.random_int(min=1, max=256)
    if not memory_usage:
        memory_usage = fake.random_int(min=0, max=memory_total)
    if not local_storage_total:
        local_storage_total = fake.random_int(min=100, max=10000)
    if not local_storage_usage:
        local_storage_usage = fake.random_int(min=0, max=local_storage_total)
    if not is_virtual:
        is_virtual = fake.boolean()
    if not os:
        os = fake.word() + " " + fake.word() + " " + fake.word()
    if not uptime:
        uptime = timedelta(days=fake.random_int(min=0, max=1000), hours=fake.random_int(min=0, max=23))
    if not nfs_shares:
        nfs_shares = [
            fake.file_path(depth=fake.random_int(min=1, max=5)) for _ in range(fake.random_int(min=0, max=5))
        ]
    if not webdav_shares:
        webdav_shares = [
            fake.file_path(depth=fake.random_int(min=1, max=5)) for _ in range(fake.random_int(min=0, max=5))
        ]
    if not packages:
        packages = [generate_package() for _ in range(fake.random_int(min=1, max=5))]
    if not service_contract:
        service_contract = generate_service_contract()
    if not people:
        people = [generate_person() for _ in range(fake.random_int(min=1, max=5))]
    if not reboot_required:
        reboot_required = fake.boolean()

    if not users:
        users = [fake.user_name() for _ in range(fake.random_int(min=1, max=5))]
    if not groups:
        groups = unique_list_picks(lists.user_groups, min=1, max=5)

    return Server(
        name=name,
        ip_address=ip_address,
        cpu_total=cpu_total,
        cpu_usage=cpu_usage,
        memory_total=memory_total,
        memory_usage=memory_usage,
        local_storage_total=local_storage_total,
        local_storage_usage=local_storage_usage,
        is_virtual=is_virtual,
        os=os,
        uptime=uptime,
        nfs_shares=nfs_shares,
        webdav_shares=webdav_shares,
        packages=packages,
        service_contract=service_contract,
        people=people,
        reboot_required=reboot_required,
        users=users,
        groups=groups,
    )
