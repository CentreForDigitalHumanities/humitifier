from pydantic import BaseModel
from humitifier.fake.gen.utils import gen_fake
from humitifier.fake.gen.person import FakePerson
from humitifier.fake.gen import facts as fake_facts
from humitifier import facts as infra_facts


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

