from pydantic import BaseModel
from humitifier.fake.gen.utils import gen_fake
from humitifier.fake.gen.person import FakePerson
from humitifier.fake.gen.package import FakePackage
from humitifier.fake.gen.servicecontract import FakeServiceContract
from humitifier.fake.gen.server import FakeServer, Server
from humitifier.fake.gen.cluster import FakeCluster, Cluster
from humitifier.fake.gen import facts as fake_facts
from humitifier.infra import facts as infra_facts
from humitifier.fake.gen.factping import FakeFactPing, FactPing


def test_gen_fake_correctly_generates_generic_class_without_kwargs():
    class Foo(BaseModel):
        bar: str
        baz: int

    class FakeFoo:
        bar = lambda: "hello"
        baz = lambda: 42

    generated = gen_fake(Foo, FakeFoo)
    assert isinstance(generated, Foo)
    assert generated.bar == "hello"
    assert generated.baz == 42


def test_gen_fake_correctly_generates_generic_class_with_kwargs():
    class Foo(BaseModel):
        bar: str
        baz: int

    class FakeFoo:
        bar = lambda: "hello"
        baz = lambda: 42

    generated = gen_fake(Foo, FakeFoo, bar="world")
    assert isinstance(generated, Foo)
    assert generated.bar == "world"
    assert generated.baz == 42


def test_gen_fake_correctly_generates_class_with_shared_kwargs():
    def gen_baz(bar: str):
        return int(bar)

    class Foo(BaseModel):
        bar: str
        baz: int

    class FakeFoo:
        bar = lambda: "42"
        baz = gen_baz

    generated = gen_fake(Foo, FakeFoo)
    assert isinstance(generated, Foo)
    assert generated.baz == 42


def test_fake_person_correctly_generates_person():
    generated = FakePerson.generate()
    assert generated.name
    assert generated.email
    assert generated.notes


def test_fake_person_correctly_generates_person_with_kwargs():
    generated = FakePerson.generate(name="John Doe")
    assert generated.name == "John Doe"
    assert generated.email.startswith("j.doe")


def test_person_pool_correctly_cycles():
    pool = FakePerson.create_pool()
    people = [next(pool) for _ in range(101)]
    assert people[0] == people[100]
    assert people[1] != people[100]


def test_fake_package_correctly_generates_package():
    generated = FakePackage.generate()
    assert generated.name
    assert generated.version


def test_fake_package_correctly_generates_package_with_kwargs():
    generated = FakePackage.generate(name="foo")
    assert generated.name == "foo"
    assert generated.version


def test_fake_service_contract_correctly_generates_service_contract():
    generated = FakeServiceContract.generate()
    assert generated.entity
    assert generated.owner
    assert generated.start_date
    assert generated.end_date
    assert generated.purpose


def test_fake_server_correctly_generates_server():
    generated = FakeServer.generate()
    assert isinstance(generated, Server)


def test_fake_cluster_correctly_generates_cluster():
    generated = FakeCluster.generate()
    assert isinstance(generated, Cluster)


def test_fake_hostname_ctl_correctly_generates_hostname_ctl():
    generated = fake_facts.FakeHostnameCtl.generate()
    assert isinstance(generated, infra_facts.HostnameCtl)


def test_fake_memory_correctly_generates_memory():
    generated = fake_facts.FakeMemory.generate()
    assert isinstance(generated, infra_facts.Memory)


def test_fake_package_correctly_generates_package():
    generated = fake_facts.FakePackage.generate()
    assert isinstance(generated, infra_facts.Package)


def test_fake_block_device_correctly_generates_block_device():
    generated = fake_facts.FakeBlock.generate()
    assert isinstance(generated, infra_facts.Block)


def test_fake_uptime_correctly_generates_uptime():
    generated = fake_facts.FakeUptime.generate()
    assert isinstance(generated, infra_facts.Uptime)


def test_fake_user_correctly_generates_user():
    generated = fake_facts.FakeUser.generate()
    assert isinstance(generated, infra_facts.User)


def test_fake_group_correctly_generates_group():
    generated = fake_facts.FakeGroup.generate()
    assert isinstance(generated, infra_facts.Group)


def test_fake_factping_correctly_generates_factping():
    generated = FakeFactPing.generate()
    assert isinstance(generated, FactPing)
