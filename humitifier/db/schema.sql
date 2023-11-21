-- name: create_facts_table#
create table if not exists host_facts (
    id integer primary key autoincrement,
    host text,
    timestamp integer,
    raw_output text,
    facts text,
    exceptions text
);