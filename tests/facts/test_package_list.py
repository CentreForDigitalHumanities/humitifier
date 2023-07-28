from humitifier.facts import PackageList
from humitifier.facts.protocols import SshFact


def test_package_list_implements_fact_protocol():
    assert isinstance(PackageList, SshFact)


def test_package_list_from_stdout():
    stdout = [
        "accountsservice	0.6.55-0ubuntu12.2",
        "acl	2.2.53-6",
        "acpid	1:2.0.32-1ubuntu1",
        "adduser	3.118ubuntu1",
        "adwaita-icon-theme	3.36.1-2ubuntu0.20.04.2",
    ]
    package_list = PackageList.from_stdout(stdout)
    assert isinstance(package_list, PackageList)
    assert len(package_list) == 5
    assert package_list[0].name == "accountsservice"
    assert package_list[0].version == "0.6.55-0ubuntu12.2"
    assert package_list[1].name == "acl"
    assert package_list[1].version == "2.2.53-6"
    assert package_list[2].name == "acpid"
    assert package_list[2].version == "1:2.0.32-1ubuntu1"
    assert package_list[3].name == "adduser"
    assert package_list[3].version == "3.118ubuntu1"
    assert package_list[4].name == "adwaita-icon-theme"
    assert package_list[4].version == "3.36.1-2ubuntu0.20.04.2"
    