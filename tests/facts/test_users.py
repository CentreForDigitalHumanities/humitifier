from humitifier.facts import Users
from humitifier.facts.protocols import SshFact


def test_users_implements_fact_protocol():
    assert isinstance(Users, SshFact)


def test_users_from_stdout():
    stdout = [
        "root:x:0:0:root:/root:/bin/bash",
        "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin",
        "bin:x:2:2:bin:/bin:/usr/sbin/nologin",
        "sys:x:3:3:sys:/dev:/usr/sbin/nologin",
        "sync:x:4:65534:sync:/bin:/bin/sync",
    ]
    users = Users.from_stdout(stdout)
    assert isinstance(users, Users)
    assert len(users) == 5
    assert users[0].name == "root"
    assert users[0].uid == 0
    assert users[0].gid == 0
    assert users[0].home == "/root"
    assert users[0].shell == "/bin/bash"
    assert users[1].name == "daemon"