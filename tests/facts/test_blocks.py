from humitifier.facts import Blocks
from humitifier.facts.protocols import SshFact


def test_blocks_implements_fact_protocol():
    assert isinstance(Blocks, SshFact)


def test_blocks_from_stdout():
    stdout = [
        "Filesystem     1M-blocks  Used Available Use% Mounted on",
        "/dev/sda1        16000  1000     14000  10% /",
        "/dev/sda2        16000  1000     14000  10% /",
    ]
    blocks = Blocks.from_stdout(stdout)
    assert isinstance(blocks, Blocks)
    assert len(blocks) == 2
    assert blocks[0].name == "/dev/sda1"
    assert blocks[0].size_mb == 16000
    assert blocks[0].used_mb == 1000
    assert blocks[0].available_mb == 14000
    assert blocks[0].use_percent == 10
    assert blocks[0].mount == "/"
    assert blocks[1].name == "/dev/sda2"
    assert blocks[1].size_mb == 16000
    assert blocks[1].used_mb == 1000
    assert blocks[1].available_mb == 14000
    assert blocks[1].use_percent == 10
    assert blocks[1].mount == "/"