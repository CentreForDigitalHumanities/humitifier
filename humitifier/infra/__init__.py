import aiosqlite
import asyncio
import time
from humitifier.logging import logging
from humitifier.infra.models.host import Host
from humitifier.infra.models.hostfacts import HostFacts
from humitifier.infra.facts import query_inventory_outputs
from humitifier.db import queries
from humitifier.config import CONFIG

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def update_fact_db():
    hosts = list(Host.load_inventory())
    ts = int(time.time())
    logger.info("Querying inventory for %s hosts", len(hosts))
    outputs = await query_inventory_outputs(hosts)
    logger.info("Parsing %s outputs", len(outputs))
    parse_tasks = [HostFacts.from_output(out, ts) for out in outputs]
    hostfacts = await asyncio.gather(*parse_tasks)
    rows = [await hf.sql_row for hf in hostfacts]
    async with aiosqlite.connect(CONFIG.db) as db:
        logger.info("Running schema create script on: %s", CONFIG.db)
        await queries.create_facts_table(db)
        logger.info("Inserting %s rows into %s", len(rows), CONFIG.db)
        await queries.bulk_insert_host_facts(db, rows)
        await db.commit()


async def retrieve_host_data():
    inventory = Host.load_inventory()

    async with aiosqlite.connect(CONFIG.db) as db:
        rows = await queries.get_latest_host_facts(db)

    facts = await asyncio.gather(*[HostFacts.from_sql_row(row) for row in rows])
    facts_kv = {f.fqdn: f for f in facts}
    hosts = [Host(fqdn=host.fqdn, metadata=host.metadata, facts=facts_kv.get(host.fqdn)) for host in inventory]
    return hosts
