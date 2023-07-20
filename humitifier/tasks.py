from rocketry import Rocketry
from humitifier.facts import Fact
from humitifier.models.factping import FactPing
from humitifier.models.host_state import HostState


def create_scheduler(app):
    task_app = Rocketry(execution="async")

    @task_app.task(app.state.config.poll_interval)
    def update_host_states():
        fact_data = Fact.collect_fact_data(client=app.state.pssh_client, facts=app.state.config.facts)
        fact_kv = FactPing.factping_kv(fact_data)
        app.state.host_states_kv = {h.fqdn: HostState(host=h, facts=fact_kv[h.fqdn]) for h in app.state.config.hosts}

    return task_app