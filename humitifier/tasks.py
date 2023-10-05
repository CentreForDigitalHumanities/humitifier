from rocketry import Rocketry
from humitifier.facts import collect_facts
from humitifier.models.host_state import HostState


def create_scheduler(app):
    task_app = Rocketry(execution="async")

    @task_app.task(app.state.config.poll_interval)
    def update_host_states():
        fact_data = collect_facts(client=app.state.pssh_client, facts=app.state.config.facts)
        app.state.host_states_kv = {h.fqdn: HostState.from_host_facts(h, fact_data) for h in app.state.config.hosts}

    return task_app
