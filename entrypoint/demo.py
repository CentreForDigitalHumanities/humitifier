import uvicorn

from humitifier.app import create_app
from humitifier.models.cluster import Cluster

from humitifier.fake.gen.server import ServerPool

servers = [next(ServerPool) for _ in range(100)]
cluster = Cluster(name="main", servers=servers)
app = create_app(cluster=cluster)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
