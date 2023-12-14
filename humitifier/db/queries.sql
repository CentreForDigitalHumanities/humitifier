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

-- name: clear_old_facts#
delete from host_facts
where (host, date(timestamp)) not in (
    select host, date(timestamp)
    from (
        select host, date(timestamp), max(timestamp) as max_timestamp
        from host_facts
        group by host, date(timestamp)
    ) as subquery
    where timestamp = max_timestamp
) and date(timestamp) < date("now", "-1 day");