import pytest
from humitifier.fake.gen.server import FakeServer
from humitifier.fake.gen.package import FakePackage
from humitifier.fake.gen.servicecontract import FakeServiceContract
from humitifier.fake.gen.person import FakePerson
from humitifier.models.cluster import Cluster


def test_cluster_filter_by_hostname():
    s1 = FakeServer.generate(hostname="foo")
    s2 = FakeServer.generate(hostname="bar")
    cluster = Cluster(name="test", servers=[s1, s2])
    filtered = cluster.apply_filters(hostname="foo")
    assert len(filtered) == 1
    assert filtered[0].hostname == "foo"


def test_cluster_filter_by_os():
    s1 = FakeServer.generate(os="foo")
    s2 = FakeServer.generate(os="bar")
    cluster = Cluster(name="test", servers=[s1, s2])
    filtered = cluster.apply_filters(os="foo")
    assert len(filtered) == 1
    assert filtered[0].os == "foo"


def test_cluster_filter_by_department():
    s1 = FakeServer.generate()
    s2 = FakeServer.generate()
    cluster = Cluster(name="test", servers=[s1, s2])
    filtered = cluster.apply_filters(entity=s1.service_contract.entity)
    assert len(filtered) == 1
    assert filtered[0].service_contract.entity == s1.service_contract.entity


def test_cluster_filter_by_owner():
    s1 = FakeServer.generate()
    s2 = FakeServer.generate()
    cluster = Cluster(name="test", servers=[s1, s2])
    filtered = cluster.apply_filters(owner=s1.service_contract.owner.name)
    assert len(filtered) == 1
    assert filtered[0].service_contract.owner.name == s1.service_contract.owner.name


def test_cluster_filter_by_purpose():
    cs1 = FakeServiceContract.generate(purpose="foo")
    cs2 = FakeServiceContract.generate(purpose="bar")
    s1 = FakeServer.generate(service_contract=cs1)
    s2 = FakeServer.generate(service_contract=cs2)
    cluster = Cluster(name="test", servers=[s1, s2])
    filtered = cluster.apply_filters(purpose=s1.service_contract.purpose)
    assert len(filtered) == 1
    assert filtered[0].service_contract.purpose == s1.service_contract.purpose


def test_cluster_filter_by_package():
    s1 = FakeServer.generate(packages=[FakePackage.generate(name="fooyou")])
    s2 = FakeServer.generate(packages=[FakePackage.generate(name="footwo")])
    cluster = Cluster(name="test", servers=[s1, s2])
    filtered = cluster.apply_filters(package="fooyou")
    assert len(filtered) == 1
    assert filtered[0].packages[0].name == s1.packages[0].name
    filtered = cluster.apply_filters(package="foo")
    assert len(filtered) == 2


def test_cluster_filter_by_contact():
    p = FakePerson.generate()
    c = FakeServiceContract.generate(people=[p])
    s1 = FakeServer.generate(service_contract=c)
    cluster = Cluster(name="test", servers=[s1])
    filtered = cluster.apply_filters(contact=p.name)
    assert len(filtered) == 1
    assert filtered[0].service_contract.people[0].name == p.name


def test_cluster_filter_by_issue():
    s1 = FakeServer.generate(service_contract=None)
    s2 = FakeServer.generate()
    cluster = Cluster(name="test", servers=[s1, s2])
    filtered = cluster.apply_filters(issue="missing-service-contract")
    assert len(filtered) == 1
    assert filtered[0].issues[0].slug == "missing-service-contract"


def test_every_filter_opt_has_a_filter():
    s1 = FakeServer.generate()
    s2 = FakeServer.generate()
    cluster = Cluster(name="test", servers=[s1, s2])
    opts = Cluster.opts(cluster.servers)
    for opt in opts:
        assert hasattr(Cluster, f"_filter_by_{opt}")


def test_get_setver_by_hostname():
    s1 = FakeServer.generate(hostname="foo")
    s2 = FakeServer.generate(hostname="bar")
    cluster = Cluster(name="test", servers=[s1, s2])
    assert cluster.get_server_by_hostname("foo") == s1
    assert cluster.get_server_by_hostname("bar") == s2
    with pytest.raises(IndexError):
        cluster.get_server_by_hostname("baz")
    s3 = FakeServer.generate(hostname="foo")
    cluster = Cluster(name="test", servers=[s1, s3])
    with pytest.raises(ValueError):
        cluster.get_server_by_hostname("foo")
