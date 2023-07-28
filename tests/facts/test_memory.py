from humitifier.facts import Memory
from humitifier.facts.protocols import SshFact


def test_memory_implements_fact_protocol():
    assert isinstance(Memory, SshFact)


def test_memory_from_stdout():
    stdout = [
        "              total        used        free      shared  buff/cache   available",
        "Mem:           16000        1000       14000           0        1000       14000",
        "Swap:          16000        1000       14000",
    ]
    memory = Memory.from_stdout(stdout)
    assert isinstance(memory, Memory)
    assert memory.total_mb == 16000
    assert memory.used_mb == 1000
    assert memory.free_mb == 14000
    assert memory.swap_total_mb == 16000
    assert memory.swap_used_mb == 1000
    assert memory.swap_free_mb == 14000