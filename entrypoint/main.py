import uvicorn
import toml

from humitifier.app import create_app
from humitifier.models.cluster import Cluster
from humitifier.models.factping import FactPing
from humitifier.infra.facts import HostnameCtl, Memory, Uptime, User, Group, Block, Package
from humitifier.models.server import Server
from humitifier.models.servicecontract import ServiceContract
from humitifier.infra.utils import PsshBuilder

with open("/data/gw-d-dh-gretel-tst.toml") as f:
    data = toml.load(f)
contract = ServiceContract.from_toml(data)
builder = PsshBuilder(hosts=[contract.fqdn], facts=[HostnameCtl, Memory, Uptime, User, Group, Block, Package])
client = builder.client(proxy_host="cratylus.im.hum.uu.nl", user="donatas")
outputs = builder.run(client)
data = builder.parse(outputs)
factping = FactPing.from_facts(data[contract.fqdn])
server = Server.create(servicecontract=contract, facts=factping)
cluster = Cluster(name="main", servers=[server])
app = create_app(cluster=cluster)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)