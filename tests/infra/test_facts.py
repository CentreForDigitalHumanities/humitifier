import pytest
from dataclasses import dataclass
from humitifier.facts import HostnameCtl, Memory, Package, Uptime, Block, Group, User, Fact


@dataclass
class MockHostOutput:
    stdout: list[str]
    host: str = "example.com"
    exit_code: int = 0
    stderr: list[str] | None = None


def test_hostnamectl_parses_cmd_output():
    out = [
        "Static hostname: myhost",
        "Operating System: Ubuntu 20.04.1 LTS",
        "CPE OS Name: cpe:/o:canonical:ubuntu_linux:20.04",
        "Kernel: Linux 5.4.0-90-generic",
        "Virtualization: kvm",
    ]
    fact = HostnameCtl.from_stdout(out)
    assert isinstance(fact, HostnameCtl)


def test_memory_parses_cmd_output():
    out = [
        "              total        used        free      shared  buff/cache   available",
        "Mem:           2000         100        1000           0         900        1000",
        "Swap:          1000           0        1000",
    ]
    fact = Memory.from_stdout(out)
    assert isinstance(fact, Memory)


def test_package_parses_cmd_output():
    out = [
        "package1\t1.0.0",
        "package2\t2.0.0",
    ]
    fact = Package.from_stdout(out)
    assert isinstance(fact, list)
    assert isinstance(fact[0], Package)


def test_uptime_parses_cmd_output():
    out = ["up 5 days, 22 hours, 52 minutes"]
    fact = Uptime.from_stdout(out)
    assert isinstance(fact, Uptime)


def test_block_parses_cmd_output():
    out = [
        "Filesystem     1M-blocks  Used Available Use% Mounted on",
        "/dev/sda1        16000  1000     14000  10% /",
        "/dev/sda2        16000  1000     14000  10% /",
    ]
    fact = Block.from_stdout(out)
    assert isinstance(fact, list)
    assert isinstance(fact[0], Block)


def test_group_parses_cmd_output():
    out = [
        "root:x:0:mary,john",
        "daemon:x:1:",
        "bin:x:2:",
        "sys:x:3:",
    ]
    fact = Group.from_stdout(out)
    assert isinstance(fact, list)
    assert isinstance(fact[0], Group)
    assert fact[0].users == ["mary", "john"]
    assert fact[1].users == []


def test_user_parses_cmd_output():
    out = [
        "root:x:0:0:root:/root:/bin/bash",
        "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin",
        "systemd-network:x:100:102:systemd Network Management,,,:/run/systemd:/usr/sbin/nologin",
    ]
    fact = User.from_stdout(out)
    assert isinstance(fact, list)
    assert isinstance(fact[0], User)



@pytest.mark.parametrize("fact", list(Fact))
def test_fact_can_generate_command(fact):
    assert isinstance(fact.cmd(None), str)


@pytest.mark.parametrize("fact", list(Fact))
def test_every_fact_has_corresponding_dataclass(fact):
    assert fact._fact_data is not None

@pytest.mark.parametrize("stdout, expected_type", [
    ([   
        "HostnameCtl",
        "Static hostname: myhost",
        "Operating System: Ubuntu 20.04.1 LTS",
        "CPE OS Name: cpe:/o:canonical:ubuntu_linux:20.04",
        "Kernel: Linux 5.4.0-90-generic",
        "Virtualization: kvm",
    ], HostnameCtl),
    ([
        "Memory",
        "              total        used        free      shared  buff/cache   available",
        "Mem:           2000         100        1000           0         900        1000",
        "Swap:          1000           0        1000",
    ], Memory),
    ([
        "Package",
        "package1\t1.0.0",
        "package2\t2.0.0",
    ], list),
    ([
        "Uptime",
        "up 5 days, 22 hours, 52 minutes"
    ], Uptime),
    ([
        "Block",
        "Filesystem     1M-blocks  Used Available Use% Mounted on",
        "/dev/sda1        16000  1000     14000  10% /",
        "/dev/sda2        16000  1000     14000  10% /",
    ], list),
    ([
        "Group",
        "root:x:0:mary,john",
        "daemon:x:1:",
        "bin:x:2:",
        "sys:x:3:",
    ], list),
    ([
        "User",
        "root:x:0:0:root:/root:/bin/bash",
        "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin",
        "systemd-network:x:100:102:systemd Network Management,,,:/run/systemd:/usr/sbin/nologin",
    ], list),
])
def test_fact_output_parse(stdout, expected_type):
    output = MockHostOutput(stdout)
    host, fact_data = Fact.parse_hostoutput(output)
    assert isinstance(fact_data, expected_type)
    assert host == output.host