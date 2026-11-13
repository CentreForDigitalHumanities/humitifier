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


def resolve_hostname_with_dns(ip: str) -> str | None:
    try:
        reverse_name = dns.reversename.from_address(ip)
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


_resolve_hostname_with_dns = resolve_hostname_with_dns


def parse_human_readable_filesize(
    size_str: str, *, assume_decimal: bool = False
) -> int | None:
    """Parse a human readable filesize string into a bytes value."""
    # We need a string of at least 2 characters ('0B' being the shortest valid value)
    if not size_str or len(size_str) <= 1:
        return None

    # split the value into size and unit by taking the last two characters as the unit
    unit = size_str[-2:]
    size = size_str[:-2]

    # A unit might also be a single character, see if the first character of our 'unit'
    # is a digit or space. If so, change our unit to only the last character
    if unit[0] in "0123456789 ":
        unit = unit[1:]
        size = size_str[:-1]

    try:
        # Strip out any whitespace ('40 Gb' for example)
        size = size.strip()
        size = float(size)
    except ValueError:
        return None

    unit = unit.upper()
    multipliers = {
        "B": 1,
        "K": 1000 if assume_decimal else 1024,
        "KB": 1000 if assume_decimal else 1024,
        "KIB": 1024,
        "M": 1000**2 if assume_decimal else 1024**2,
        "MB": 1000**2 if assume_decimal else 1024**2,
        "MIB": 1024**2,
        "G": 1000**3 if assume_decimal else 1024**3,
        "GB": 1000**3 if assume_decimal else 1024**3,
        "GIB": 1024**3,
        "T": 1000**4 if assume_decimal else 1024**4,
        "TB": 1000**4 if assume_decimal else 1024**4,
        "TIB": 1024**4,
    }

    if unit not in multipliers:
        return None

    return int(size * multipliers[unit])
