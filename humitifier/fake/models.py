from humitifier.fake.helpers import server_opts
from humitifier.models import Server


def fake_server(**kwargs) -> Server:
    base = server_opts()
    merged = {**base, **kwargs}
    return Server(**merged)
