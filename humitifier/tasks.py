import asyncpg
import json
import time
from datetime import datetime
from rocketry import Rocketry
from rocketry.conds import after_success, hourly
from pssh.output import HostOutput
from humitifier import facts
from humitifier.config import CONFIG, PSSH_CLIENT
from humitifier.logging import logging
from humitifier.utils import FactError

app = Rocketry(execution="async")


def serialize_output(output: HostOutput) -> dict:
    return {
        "host": output.host,
        "exception": str(output.exception) if output.exception else None,
        "exit_code": output.exit_code,
        "stdout": "\n".join(list(output.stdout)),
        "stderr": "\n".join(list(output.stderr)),
    }


def collect_outputs(fact_name: str, ts: datetime, cmd: str) -> list[dict]:
    fact_meta = {"name": fact_name, "scan": ts}
    outs = PSSH_CLIENT.run_command(cmd)
    PSSH_CLIENT.join(outs)
    return [{**fact_meta, **serialize_output(out)} for out in outs]


def parse_row_data(row) -> facts.SshFact | FactError:
    cls = getattr(facts, row["name"])
    try:
        return cls.from_stdout(row["stdout"].split("\n"))
    except Exception as e:
        return FactError(
            stdout=row["stdout"],
            stderr=row["stderr"],
            exception=row["exception"],
            exit_code=row["exit_code"],
            py_excpetion=str(e),
        )


@app.task(hourly)
async def sync_hosts():
    time.sleep(5)
    logging.info("Syncing hosts")
    conn = await asyncpg.connect(CONFIG.db)
    await conn.execute("""SELECT sync_hosts($1)""", CONFIG.inventory)
    await conn.close()


@app.task(after_success(sync_hosts))
async def scan_hosts():
    logging.info("Initiating scan of hosts")
    ts = datetime.now()
    conn = await asyncpg.connect(CONFIG.db)
    await conn.execute("""INSERT INTO scans(ts) VALUES ($1)""", ts)

    fact_outputs = []

    for fact in facts.SSH_FACTS:
        logging.info(f"Querying {fact.__name__}...")
        fact_outputs.extend(collect_outputs(fact.__name__, ts, fact.cmd))
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
    logging.info("Parsing facts")
    conn = await asyncpg.connect(CONFIG.db)
    rows = await conn.fetch("""SELECT name, host, scan, stdout, stderr, exception, exit_code FROM host_outputs""")
    parsed_rows = [(row["name"], row["host"], row["scan"], parse_row_data(row)) for row in rows]
    await conn.executemany(
        """INSERT INTO facts(name, host, scan, data) VALUES($1, $2, $3, $4)""",
        [(name, host, scan, json.dumps(parsed.to_sql())) for name, host, scan, parsed in parsed_rows],
    )
    await conn.execute("DELETE FROM host_outputs")
    await conn.close()
