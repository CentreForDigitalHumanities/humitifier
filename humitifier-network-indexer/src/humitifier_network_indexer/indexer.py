import ipaddress
import socket

import dns.reversename, dns.resolver
from dns.resolver import NXDOMAIN
from humitifier_common.index_data import (
    IndexIPInput,
    IndexedIP,
)

from .network import NetworkExecutor, NetworkError


def index_ipv4(input: IndexIPInput) -> IndexedIP:
    ip_address = ipaddress.IPv4Address(input.ip_address)

    output = IndexedIP(ip_address=str(ip_address))

    active_state = get_active_state(ip_address)
    output.active = active_state["active"]
    output.ping_time = active_state["time_avg"]

    output.reverse_dns = get_reverse_dns(ip_address)

    output.ports = get_open_ports(ip_address, input.ports)

    return output


def get_active_state(
    ip: ipaddress.IPv4Address | ipaddress.IPv6Address, ping_count=4
) -> dict:
    executor = NetworkExecutor()
    try:
        ping_results = executor.ping(str(ip), count=ping_count)

        can_ping = ping_results.received == ping_count
        time_avg = ping_results.avg_time
    except NetworkError:
        return {"active": False, "time_avg": None}

    return {"active": can_ping, "time_avg": time_avg}


def get_open_ports(
    ip: ipaddress.IPv4Address | ipaddress.IPv6Address, ports: list[int]
) -> dict:
    open_ports = {}

    for port in ports:
        try:
            with socket.create_connection((str(ip), port), timeout=2):
                open_ports[port] = True
        except OSError:
            open_ports[port] = False

    return open_ports


def get_reverse_dns(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> list[str]:

    reverse_name = dns.reversename.from_address(str(ip))

    try:
        resolved_hosts = dns.resolver.resolve(reverse_name, "PTR")
        reverse_dns_lookups = [str(host) for host in resolved_hosts]
    except NXDOMAIN:
        reverse_dns_lookups = []

    return reverse_dns_lookups
