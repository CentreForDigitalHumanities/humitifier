-- name: create_schema#
create table servers (
    id integer primary key,
    name text,
    ip_address text,
    cpu_total integer,
    cpu_usage real,
    memory_total integer,
    memory_usage integer,
    local_storage_total integer,
    local_storage_usage integer,
    is_virtual integer,
    os text,
    uptime integer,
    nfs_shares text,
    webdav_shares text,
    requesting_department text,
    server_type text,
    contact_persons text,
    expiry_date integer,
    update_policy text,
    available_updates text,
    reboot_required integer,
    users text,
    groups text,
    installed_packages text
);