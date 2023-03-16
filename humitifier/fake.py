from faker import Faker
from humitifier.models import Server
from datetime import timedelta

fake = Faker()
linux_packages = [
    "python3",
    "mysql-server",
    "nginx",
    "apache2",
    "php",
    "postgresql",
    "git",
    "vim",
    "wget",
    "curl",
    "nodejs",
    "npm",
    "docker",
    "openssh-server",
    "fail2ban",
    "ufw",
    "rsync",
    "tcpdump",
    "htop",
    "zip",
]
user_groups = ["admins", "backoffice", "developers", "sudoers"]


def create_server(
    name=None,
    ip_address=None,
    cpu_total=None,
    cpu_usage=None,
    memory_total=None,
    memory_usage=None,
    local_storage_total=None,
    local_storage_usage=None,
    is_virtual=None,
    os=None,
    uptime=None,
    nfs_shares=None,
    webdav_shares=None,
    requesting_department=None,
    server_type=None,
    contact_persons=None,
    expiry_date=None,
    update_policy=None,
    available_updates=None,
    reboot_required=None,
    users=None,
    groups=None,
    installed_packages=None,
) -> Server:
    return Server(
        name=name or fake.hostname(),
        ip_address=ip_address or fake.ipv4_private(),
        cpu_total=cpu_total or fake.random_int(min=1, max=64),
        cpu_usage=cpu_usage or fake.pyfloat(left_digits=2, right_digits=1, positive=True, max_value=100),
        memory_total=memory_total or fake.random_int(min=1, max=8),
        memory_usage=memory_usage or fake.random_int(min=1, max=8),
        local_storage_total=local_storage_total or fake.random_int(min=100, max=10000),
        local_storage_usage=local_storage_usage or fake.random_int(min=1, max=5000),
        is_virtual=is_virtual or fake.boolean(),
        os=os or fake.random_element(elements=("Ubuntu 20.04 LTS", "Debian 11", "CentOS 9", "Fedora 8", "Arch Linux")),
        uptime=uptime or timedelta(days=fake.random_int(min=1, max=365)),
        nfs_shares=nfs_shares or [fake.file_path(depth=fake.random_int(min=1, max=5)) for _ in range(2)],
        webdav_shares=webdav_shares or [fake.uri_path(deep=fake.random_int(min=1, max=5)) for _ in range(2)],
        requesting_department=requesting_department or fake.random_element(elements=("IT", "Sales", "Marketing")),
        server_type=server_type
        or fake.random_element(elements=("Web Server", "Database Server", "Application Server")),
        contact_persons=contact_persons or [fake.email() for _ in range(fake.random_int(min=1, max=5))],
        expiry_date=expiry_date or fake.future_datetime(end_date="+5y"),
        update_policy=update_policy or fake.random_element(elements=("automatic", "manual")),
        available_updates=available_updates
        or list(set([fake.random_element(elements=linux_packages) for _ in range(fake.random_int(min=0, max=20))])),
        reboot_required=reboot_required or fake.boolean(),
        users=users or list(set([fake.user_name() for _ in range(fake.random_int(min=1, max=15))])),
        groups=groups
        or list(set([fake.random_element(elements=user_groups) for _ in range(fake.random_int(min=1, max=5))])),
        installed_packages=installed_packages
        or list(set([fake.random_element(elements=linux_packages) for _ in range(20)])),
    )
