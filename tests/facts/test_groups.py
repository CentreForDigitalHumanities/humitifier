from humitifier.facts import Groups
from humitifier.facts.protocols import SshFact


def test_groups_implements_fact_protocol():
    assert isinstance(Groups, SshFact)


def test_groups_from_stdout():
    stdout = [
        "root:x:0:",
        "daemon:x:1:",
        "bin:x:2:",
        "sys:x:3:",
        "adm:x:4:syslog,ubuntu",
    ]
    groups = Groups.from_stdout(stdout)
    assert isinstance(groups, Groups)
    assert len(groups) == 5
    assert groups[0].name == "root"
    assert groups[0].gid == 0
    assert groups[0].users == []
    assert groups[1].name == "daemon"
    assert groups[1].gid == 1
    assert groups[1].users == []
    assert groups[2].name == "bin"
    assert groups[2].gid == 2
    assert groups[2].users == []