from humitifier.models.host_state import HostState
from .utils import gen_fake
from .host import FakeHost
from .factping import FakeFactPing


class FakeHostState:
    host = lambda: FakeHost.generate()
    facts = lambda: FakeFactPing.generate()

    @classmethod
    def generate(cls, **kwargs) -> HostState:
        return gen_fake(HostState, cls, **kwargs)
