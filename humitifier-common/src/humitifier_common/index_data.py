from pydantic import BaseModel, ConfigDict


class IndexIPInput(BaseModel):
    ip_address: str
    ports: list[int] = []


class IndexedIP(BaseModel):
    ip_address: str
    active: bool = False
    ping_time: float | None = None
    reverse_dns: list[str] = []
    ports: dict[int, bool] = {}
