import asyncpg
import json
import time
from datetime import datetime
from rocketry import Rocketry
from rocketry.conds import after_success, hourly
from pssh.clients import ParallelSSHClient
from pssh.output import HostOutput
from ssh2.exceptions import SocketRecvError
from humitifier import facts
from humitifier.config import CONFIG, PSSH_CLIENT, Config
from humitifier.logging import logging
from humitifier.utils import FactError

logger = logging.getLogger(__name__)

app = Rocketry(execution="async")

ERR_SOCKET_RECV_ERROR = "SocketRecvError"


def serialize_output(output: HostOutput) -> dict:
    return {
        "host": output.host,
        "exception": str(output.exception) if output.exception else None,
        "exit_code": output.exit_code,
        "stdout": "\n".join(list(output.stdout)) if output.stdout else None,
        "stderr": "\n".join(list(output.stderr)) if output.stderr else None,
    }


def parse_row_data(row) -> facts.SshFact | FactError:
    cls = getattr(facts, row["name"])
    try:
        return cls.from_stdout(row["stdout"].split("\n"))
    except Exception as e:
        logger.info(f"Error parsing {row['name']}: {e}\nData: {row}")
        return FactError(
            stdout=row["stdout"],
            stderr=row["stderr"],
            exception=row["exception"],
            exit_code=row["exit_code"],
            py_excpetion=str(e),
        )


@app.task(hourly)
async def sync_hosts():
    time.sleep(2)
    logger.info("Syncing hosts")
    cfg = Config.load()  # Reload the config with latest inventory
    conn = await asyncpg.connect(CONFIG.db)
    await conn.execute("""SELECT sync_hosts($1)""", cfg.inventory)
    await conn.close()


@app.task(after_success(sync_hosts))
async def scan_hosts():
    logger.info("Initiating scan of hosts")
    ts = datetime.now()
    conn = await asyncpg.connect(CONFIG.db)
    await conn.execute("""INSERT INTO scans(ts) VALUES ($1)""", ts)

    fact_outputs = []
    skip_hosts = set()
    hosts = await conn.fetch("SELECT fqdn FROM hosts")
    hosts = [host["fqdn"] for host in hosts]

    for fact in facts.SSH_FACTS:
        client = ParallelSSHClient([x for x in hosts if x not in skip_hosts], **CONFIG.pssh)
        logger.info(f"Querying {fact.__name__}...")
        fact_meta = {"name": fact.__name__, "scan": ts}
        host_outputs = client.run_command(fact.cmd, stop_on_errors=False, read_timeout=10)
        client.join(host_outputs)
        for output in host_outputs:
            if output.exception:
                skip_hosts.add(output.host)
            fact_outputs.append({**fact_meta, **serialize_output(output)})
    await conn.executemany(
        """INSERT INTO host_outputs(name, host, scan, stdout, stderr, exception, exit_code) 
                                VALUES($1, $2, $3, $4, $5, $6, $7)""",
        [
            (
                output["name"],
                output["host"],
                output["scan"],
                output["stdout"],
                output["stderr"],
                output["exception"],
                output["exit_code"],
            )
            for output in fact_outputs
        ],
    )
    await conn.close()


@app.task(after_success(scan_hosts))
async def parse_facts():
    logger.info("Parsing facts")
    conn = await asyncpg.connect(CONFIG.db)
    rows = await conn.fetch("""SELECT name, host, scan, stdout, stderr, exception, exit_code FROM host_outputs""")
    parsed_rows = [(row["name"], row["host"], row["scan"], parse_row_data(row)) for row in rows]
    await conn.executemany(
        """INSERT INTO facts(name, host, scan, data) VALUES($1, $2, $3, $4)""",
        [(name, host, scan, json.dumps(parsed.to_sql())) for name, host, scan, parsed in parsed_rows],
    )
    await conn.execute("DELETE FROM host_outputs")
    await conn.close()
