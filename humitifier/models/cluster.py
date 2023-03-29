from pydantic import BaseModel
from .server import Server


class Cluster(BaseModel):
    name: str
    servers: list[Server]
