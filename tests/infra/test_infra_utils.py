import pytest
from humitifier.infra.facts import Fact, Uptime
from humitifier.infra.utils import generate_cmd, PsshBuilder
from pssh.clients import ParallelSSHClient
from dataclasses import dataclass
from typing import Iterator
from unittest.mock import patch


@dataclass
class MockOutput:
    host: str
    stdout: Iterator[str]
    stderr: Iterator[str]
    exit_code: int | None


def test_all_defined_facts_have_generate_cmd_function():
    for fact in Fact.__args__:
        cmd = generate_cmd(fact, "host")
        assert isinstance(cmd, str)


def test_pssh_builder_client_generates_correct_pssh_client():
    hostnames = ["host1", "host2"]
    builder = PsshBuilder(hostnames, Fact.__args__)
    client = builder.client()
    assert isinstance(client, ParallelSSHClient)


def test_full_happy_flow_pssh_builder():
    hosts = ["host"]
    builder = PsshBuilder(hosts=hosts, facts=[Uptime])
    client = builder.client()
    with (
        patch("humitifier.infra.utils.ParallelSSHClient.run_command") as mock_run,
        patch("humitifier.infra.utils.ParallelSSHClient.join") as mock_join,
    ):
        mock_run.return_value = [
            MockOutput(host="host", stdout=(x for x in ["up 5 days, 22 hours, 52 minutes"]), stderr=None, exit_code=0)
        ]
        mock_join.return_value = None
        outputs = builder.run(client)
    facts = builder.parse(outputs)
    assert facts["host"]
    assert len(facts["host"]) == 1
    assert isinstance(facts["host"][0], Uptime)
