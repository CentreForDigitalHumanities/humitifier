from humitifier.filters import *
from humitifier.fake.gen.facts import FakeHostnameCtl
from humitifier.fake.gen.factping import FakeFactPing


def test_hostfilter_apply():
    f = HostFilter()
    fakeping = FakeFactPing.generate(hostnamectl=FakeHostnameCtl.generate(hostname="Woolooloo"))
    assert f(None, fakeping, "Woolooloo")
    assert not f(None, fakeping, "malala")

def test_hostfilter_opts():
    f = HostFilter()
    fakeping = FakeFactPing.generate(hostnamectl=FakeHostnameCtl.generate(hostname="Woolooloo"))
    assert f.options([(None, fakeping)]) == ["Woolooloo"]

def test_hostfilter_opts_no_hostname():
    f = HostFilter()
    fakeping = FakeFactPing.generate(hostnamectl=None)
    assert f.options([(None, fakeping)]) == []


def test_osfilter_apply():
    f = OsFilter()
    fakeping = FakeFactPing.generate(hostnamectl=FakeHostnameCtl.generate(os="Woolooloo"))
    assert f(None, fakeping, "Woolooloo")
    assert not f(None, fakeping, "malala")

def test_osfilter_opts():
    f = OsFilter()
    fakeping = FakeFactPing.generate(hostnamectl=FakeHostnameCtl.generate(os="Woolooloo"))
    assert f.options([(None, fakeping)]) == ["Woolooloo"]

def test_osfilter_opts_no_os():
    f = OsFilter()
    fakeping = FakeFactPing.generate(hostnamectl=None)
    assert f.options([(None, fakeping)]) == []
