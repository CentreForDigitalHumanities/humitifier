from typing import Literal
from humitifier.facts import SSH_FACTS
from humitifier.utils import FactError

SEVERITY = Literal["info", "warning", "critical"]


def has_fact_error(host):
    """One or more facts could not be collected"""
    for f in SSH_FACTS:
        fact = getattr(host.facts, f.__name__)
        if not isinstance(fact, f):
            return "critical"


def puppet_agent_disabled(host):
    """Puppet agent is disabled"""
    if getattr(host.facts.PuppetAgentStatus, "disabled"):
        return "critical"


ALERTS = [has_fact_error, puppet_agent_disabled]
