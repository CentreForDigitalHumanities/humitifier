from ipaddress import IPv4Address

from humitifier_common.celery.task_names import (
    NETWORK_INDEXER_INDEX_IP,
)
from humitifier_common.index_data import (
    IndexIPInput,
    IndexedIP,
)
from .config import app
from ..indexer import index_ipv4


@app.task(name=NETWORK_INDEXER_INDEX_IP, pydantic=True)
def index_ipv4_task(ip: IndexIPInput) -> IndexedIP:
    return index_ipv4(ip)
