import platform
import socket

import dns.reversename, dns.resolver

from .config import CONFIG


def os_in_list(os: str, os_list: list[str]) -> bool:
    os_lwr = os.lower()

    return any(os_item in os_lwr for os_item in os_list)


def get_local_fqdn():
    """
    Retrieve the fully qualified domain name (FQDN) of the local machine.
    The function first checks if a local hostname is explicitly configured in `CONFIG.local_host`.
    If not, it attempts to determine the local IP address and resolve it to a hostname using DNS.
    If both methods fail, it falls back to the system's default hostname. (Which
    might be a FQDN, but is not guaranteed to be)

    Returns:
        str: The FQDN of the local machine, or the hostname if the FQDN cannot be determined.
    """
    if CONFIG.local_host:
        return CONFIG.local_host

    if ip := _get_local_ip():
        if hostname := _resolve_hostname_with_dns(ip):
            return hostname

    return platform.node()


def _get_local_ip() -> str | None:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Fail fast, the IP won't respond
    s.settimeout(0)
    try:
        # doesn't have to be reachable
        s.connect(("10.254.254.254", 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = None
    finally:
        s.close()

    return ip


def _resolve_hostname_with_dns(ip: str) -> str | None:
    reverse_name = dns.reversename.from_address(ip)

    try:
        resolved_hosts = dns.resolver.resolve(reverse_name, "PTR")

        for host in resolved_hosts:
            if not host:
                continue
            hostname = str(host)
            if not hostname:
                continue

            if hostname.endswith("."):
                return hostname[:-1]

            return hostname
    except Exception:
        return None
