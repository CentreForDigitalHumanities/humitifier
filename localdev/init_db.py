import asyncio
import aiosql
import sqlite3
import os
from humitifier import fake

if os.path.exists(".scribble/local.db"):
    os.remove(".scribble/local.db")

db = aiosql.from_path("db", "sqlite3")


def main() -> None:
    servers = [fake.create_server().to_query() for _ in range(0, 100)]
    with sqlite3.connect(".scribble/local.db") as conn:
        db.schema.create_schema(conn)
        db.queries.server_bulk_insert(conn, servers)


main()
