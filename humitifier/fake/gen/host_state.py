from humitifier.models.host_state import HostState
from .utils import gen_fake
from .facts import FactKV
from .host import FakeHost


class FakeHostState:
    host = lambda: FakeHost.generate()
    facts = lambda: FactKV.generate()

    @classmethod
    def generate(cls, **kwargs) -> HostState:
        return gen_fake(HostState, cls, **kwargs)
