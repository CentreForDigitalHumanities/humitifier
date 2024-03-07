create table if not exists hosts(
    fqdn text primary key
);

create table if not exists scans(
    ts timestamp primary key default current_timestamp
);

create table if not exists host_outputs(
    name text,
    host text references hosts(fqdn) on delete cascade,
    scan timestamp references scans(ts) on delete cascade, 
    stdout text,
    stderr text default null,
    exception text default null,
    exit_code integer,
    primary key (name, host, scan)
);

create table if not exists facts(
    name text,
    host text references hosts(fqdn) on delete cascade,
    scan timestamp references scans(ts) on delete cascade, 
    data jsonb,
    primary key (name, host, scan)
);
