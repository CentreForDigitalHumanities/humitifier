import pytest
from humitifier.infra.facts import Fact, Uptime
from humitifier.infra.utils import generate_cmd, PsshBuilder, parse_output
from pssh.clients import ParallelSSHClient
from dataclasses import dataclass
from typing import Iterator
from unittest.mock import patch


@dataclass
class MockOutput:
    host: str
    alias: str
    stdout: Iterator[str]
    stderr: Iterator[str]
    exit_code: int | None


def test_all_defined_facts_have_generate_cmd_function():
    for fact in Fact.__args__:
        cmd = generate_cmd(fact, "host")
        assert isinstance(cmd, str)


def test_pssh_builder_generates_correct_pssh_args():
    hostnames = ["host1", "host2"]
    builder = PsshBuilder(hostnames, Fact.__args__)
    assert len(builder.client_hosts) == len(builder.configs) == len(builder.commands)
    assert len(builder.host_fact_product) == len(Fact.__args__) * len(hostnames)


def test_pssh_builder_client_generates_correct_pssh_client():
    hostnames = ["host1", "host2"]
    builder = PsshBuilder(hostnames, Fact.__args__)
    client = builder.client()
    assert isinstance(client, ParallelSSHClient)


def test_pssh_builder_run_generates_correct_pssh_outputs():
    hostnames = ["host1", "host2"]
    builder = PsshBuilder(hostnames, Fact.__args__)
    client = builder.client()
    with patch("humitifier.infra.utils.PsshBuilder.run") as mock_run:
        mock_run.return_value = [
            MockOutput(host="waah", alias="eeeeh", stdout=(x for x in ["a", "a", "a"]), stderr=None, exit_code=0)
        ]
        outputs = builder.run(client)
    assert len(outputs) == 1


def test_parse_ouput_ok_with_valid_config():
    output = MockOutput(
        host="waah",
        alias=Uptime.__name__,
        stdout=(x for x in ["up 5 days, 22 hours, 52 minutes"]),
        stderr=None,
        exit_code=0,
    )
    parsed = parse_output(output)
    assert isinstance(parsed, Uptime)


def test_parse_output_raises_err_on_invalid_alias():
    output = MockOutput(
        host="waah",
        alias="eeeeh",
        stdout=(x for x in ["up 5 days, 22 hours, 52 minutes"]),
        stderr=None,
        exit_code=0,
    )
    with pytest.raises(AttributeError):
        parse_output(output)


def test_parse_output_raises_err_on_exit_code_err():
    output = MockOutput(
        host="waah",
        alias=Uptime.__name__,
        stdout=(x for x in ["up 5 days, 22 hours, 52 minutes", "up 5 days, 22 hours, 52 minutes"]),
        stderr=None,
        exit_code=None,
    )
    with pytest.raises(RuntimeError):
        parse_output(output)
