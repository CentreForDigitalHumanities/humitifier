from humitifier.facts import Uptime
from humitifier.facts.protocols import SshFact


def test_uptime_implements_fact_protocol():
    assert isinstance(Uptime, SshFact)


def test_uptime_from_stdout():
    stdout = [
        "up 6 days, 9 hours, 27 minutes",
    ]
    uptime = Uptime.from_stdout(stdout)
    assert isinstance(uptime, Uptime)
    assert uptime.days == 6
