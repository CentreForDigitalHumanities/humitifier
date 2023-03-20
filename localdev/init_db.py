import aiosql
import sqlite3
import os
from humitifier.fake.models import fake_server

if os.path.exists(".scribble/local.db"):
    os.remove(".scribble/local.db")

db = aiosql.from_path("db", "sqlite3")


def main() -> None:
    servers = [fake_server().serialize() for _ in range(0, 100)]
    with sqlite3.connect(".scribble/local.db") as conn:
        db.schema.create_schema(conn)
        db.queries.server_bulk_insert(conn, servers)


main()
