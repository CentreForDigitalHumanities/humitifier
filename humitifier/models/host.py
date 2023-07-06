from pydantic import BaseModel
from typing import Any


class Host(BaseModel):
    fqdn: str
    metadata: dict[str, Any] | None