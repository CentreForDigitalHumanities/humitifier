-- name: create_facts_table#
create table if not exists host_facts (
    id integer primary key autoincrement,
    host text,
    timestamp integer,
    facts text,
    exceptions text
);