from faker import Faker
from datetime import date, timedelta
from humitifier.fake import lists
from humitifier.fake.helpers import unique_list_picks, generate_full_name, generate_email, generate_username
from humitifier.models import Server, Person, ServiceContract, Package
from typing import Literal

fake = Faker()


def generate_person(
    name: str | None = None,
    email: str | None = None,
    role: Literal["admin", "user", "developer", "researcher"] | None = None,
    department: str | None = None,
    notes: str | None = None,
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
    entity: str | None = None,
    owner: Person | None = None,
    creation_date: date | None = None,
    expiry_date: date | None = None,
    purpose: str | None = None,
    people: list[Person] | None = None,
) -> ServiceContract:
    if not entity:
        entity = fake.random_element(elements=lists.departments)
    if not owner:
        owner = generate_person()
    if not creation_date:
        creation_date = fake.date_between(start_date="-1y", end_date="today")
    if not expiry_date:
        expiry_date = fake.date_between(start_date=creation_date, end_date="+1y")
    if not purpose:
        purpose = fake.random_element(elements=lists.applications)
    if not people:
        people = [generate_person() for _ in range(fake.random_int(min=1, max=5))]
    return ServiceContract(
        entity=entity,
        owner=owner,
        creation_date=creation_date,
        expiry_date=expiry_date,
        purpose=purpose,
        people=people,
    )


def generate_package(name: str | None = None, version: str | None = None) -> Package:
    if not name:
        name = fake.random_element(elements=lists.packages)
    if not version:
        version = f"{fake.random_int(min=1, max=10)}.{fake.random_int(min=1, max=10)}.{fake.random_int(min=1, max=10)}-{fake.word()}{fake.random_int(min=1, max=10)}{fake.word()}"
    return Package(name=name, version=version)


def generate_server(
    name: str | None = None,
    ip_address: str | None = None,
    cpu_total: int | None = None,
    cpu_usage: float | None = None,
    memory_total: int | None = None,
    memory_usage: int | None = None,
    local_storage_total: int | None = None,
    local_storage_usage: int | None = None,
    is_virtual: bool | None = None,
    os: str | None = None,
    uptime: timedelta | None = None,
    nfs_shares: list[str] | None = None,
    webdav_shares: list[str] | None = None,
    packages: list[Package] | None = None,
    service_contract: ServiceContract | None = None,
    reboot_required: bool | None = None,
    users: list[str] | None = None,
    groups: list[str] | None = None,
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
        memory_total = fake.random_int(min=1, max=32)
    if not memory_usage:
        memory_usage = fake.random_int(min=0, max=memory_total)
    if not local_storage_total:
        local_storage_total = fake.random_int(min=100, max=10000)
    if not local_storage_usage:
        local_storage_usage = fake.random_int(min=0, max=local_storage_total)
    if not is_virtual:
        is_virtual = fake.boolean()
    if not os:
        os = fake.random_element(elements=lists.operating_systems)
    if not uptime:
        uptime = timedelta(days=fake.random_int(min=0, max=1000), hours=fake.random_int(min=0, max=23))
    if not nfs_shares:
        nfs_shares = [
            fake.file_path(depth=fake.random_int(min=1, max=3)) for _ in range(fake.random_int(min=0, max=3))
        ]
    if not webdav_shares:
        webdav_shares = [
            fake.file_path(depth=fake.random_int(min=1, max=3)) for _ in range(fake.random_int(min=0, max=3))
        ]
    if not packages:
        packages = [generate_package() for _ in range(fake.random_int(min=1, max=5))]
    if not service_contract:
        service_contract = generate_service_contract()

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
        reboot_required=reboot_required,
        users=users,
        groups=groups,
    )
