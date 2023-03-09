from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Literal


@dataclass
class Host:
    """A server hosted by HUM-IT"""

    id: str
    ip: str
    type: str
    os: str
    uptime: int
    last_update: datetime
    designation: str


@dataclass
class Web:
    """A webservice that is deployed on a HUM-IT server"""

    id: str
    host_id: str
    fqdn: str
    sitemap: Optional[str]


@dataclass
class RawHostHB:
    """The raw output of an arbitrary heartbeat check on a host"""

    host_id: str
    datetime: datetime
    output: str
    type: Literal["bolt"]


@dataclass
class RawWebHB:
    """The raw output of an arbitrary heartbeat check on a webservice"""

    web_id: str
    datetime: datetime
    output: str
    type: Literal["axe", "webxray", "lighthouse"]
