from pydantic import BaseModel
from humitifier.fake.gen.utils import gen_fake
from humitifier.fake.gen.person import FakePerson
from humitifier.fake.gen.package import FakePackage
from humitifier.fake.gen.servicecontract import FakeServiceContract
from humitifier.fake.gen.server import FakeServer, Server
from humitifier.fake.gen.cluster import FakeCluster, Cluster


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
