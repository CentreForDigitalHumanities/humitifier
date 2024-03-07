from typing import Literal
from dataclasses import asdict
from humitifier.utils import FactError

SEVERITY = Literal["info", "warning", "critical"]


def has_fact_error(host):
    """One or more facts could not be collected"""
    if any([isinstance(fact, FactError) for fact in asdict(host.facts).values()]):
        return "critical"


ALERTS = [has_fact_error]
