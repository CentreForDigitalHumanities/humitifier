from humitifier.facts import HostnameCtl
from humitifier.facts.protocols import SshFact


def test_hostnamectl_implements_fact_protocol():
    assert isinstance(HostnameCtl, SshFact)


def test_hostnamectl_from_stdout():
    stdout = [
        "   Static hostname: ubuntu",
        "         Icon name: computer-vm",
        "           Chassis: vm",
        "        Machine ID: 1234567890abcdef1234567890abcdef",
        "           Boot ID: 1234567890abcdef1234567890abcdef",
        "    Virtualization: kvm",
        "  Operating System: Ubuntu 20.04.2 LTS",
        "            Kernel: Linux 5.4.0-77-generic",
        "      Architecture: x86-64",
    ]
    hostnamectl = HostnameCtl.from_stdout(stdout)
    assert isinstance(hostnamectl, HostnameCtl)
    assert hostnamectl.hostname == "ubuntu"
    assert hostnamectl.os == "Ubuntu 20.04.2 LTS"
    assert hostnamectl.cpe_os_name is None
    assert hostnamectl.kernel == "Linux 5.4.0-77-generic"
    assert hostnamectl.virtualization == "kvm"
    