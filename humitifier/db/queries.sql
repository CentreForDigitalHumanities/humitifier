-- name: bulk_insert_host_facts*!
insert into
    host_facts (host, timestamp, raw_output, facts, exceptions)
values
    (
        :host,
        :timestamp,
        :raw_output,
        :facts,
        :exceptions
    );

-- name: get_latest_host_facts
select
    host,
    timestamp,
    raw_output,
    facts,
    exceptions
from
    host_facts
where
    timestamp = (
        select
            max(timestamp)
        from
            host_facts
    )
order by
    host;