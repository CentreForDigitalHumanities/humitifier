import random
from faker import Faker
from datetime import timedelta, date
from humitifier.fake import lists

fake = Faker()
TODAY = date.today()


def generate_full_name():
    return random.choice(lists.first_names) + " " + random.choice(lists.last_names)


def generate_username(full_name: str) -> str:
    first_name = full_name.split()[0]
    last_name = full_name.split()[-1]
    return f"{first_name[:3]}_{last_name[:3]}"


def generate_email(username: str) -> str:
    domain = random.choice(lists.domains)
    return f"{username}@{domain}"


def generate_person_args() -> tuple[str, str, str]:
    full_name = generate_full_name()
    username = generate_username(full_name)
    email = generate_email(username)
    return full_name, username, email


def unique_list_picks(source: list, min: int, max: int) -> list:
    target_count = fake.random_int(min=min, max=max)
    result = []
    while len(result) != target_count:
        pick = fake.random_element(source)
        if pick not in result:
            result.append(pick)
    return result


def server_opts() -> dict:
    total_memory = fake.random_int(min=2, max=8)
    local_storage_total = fake.random_int(min=100, max=10000)
    packages = unique_list_picks(lists.packages, min=10, max=20)
    return {
        "name": fake.hostname(),
        "ip_address": fake.ipv4_private(),
        "cpu_total": fake.random_int(min=2, max=64),
        "cpu_usage": fake.pyfloat(left_digits=2, right_digits=1, positive=True, max_value=100),
        "memory_total": total_memory,
        "memory_usage": total_memory / fake.random_int(min=1, max=8),
        "local_storage_total": local_storage_total,
        "local_storage_usage": int(local_storage_total / fake.random_int(min=1, max=8)),
        "is_virtual": fake.boolean(),
        "os": fake.random_element(lists.operating_systems),
        "uptime": timedelta(days=fake.random_int(min=1, max=365)),
        "nfs_shares": [fake.file_path(depth=fake.random_int(min=1, max=5)) for _ in range(2)],
        "webdav_shares": [fake.file_path(depth=fake.random_int(min=1, max=5)) for _ in range(2)],
        "requesting_department": fake.random_element(lists.departments),
        "server_type": fake.random_element(lists.applications),
        "contact_persons": unique_list_picks(
            [", ".join([name, email]) for name, _, email in lists.staff], min=1, max=5
        ),
        "creation_date": fake.date_between(TODAY - timedelta(days=365), TODAY),
        "expiry_date": fake.date_between(TODAY, TODAY + timedelta(days=365)),
        "update_policy": fake.random_element(elements=("automatic", "manual")),
        "installed_packages": packages,
        "available_updates": unique_list_picks(packages, min=0, max=len(packages)),
        "reboot_required": fake.boolean(),
        "users": unique_list_picks([username for _, username, _ in lists.staff], min=2, max=10),
        "groups": unique_list_picks(lists.user_groups, min=1, max=5),
    }
