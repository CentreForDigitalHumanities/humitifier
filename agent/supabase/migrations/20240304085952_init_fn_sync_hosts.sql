CREATE OR REPLACE FUNCTION sync_hosts(new_hosts TEXT[])
RETURNS VOID AS $$
DECLARE
    hosts_to_add TEXT[];
BEGIN
    -- Delete hosts not in the new list
    DELETE FROM hosts WHERE fqdn NOT IN (SELECT unnest FROM unnest(new_hosts));

    -- Find hosts from the new list that are not already in the database
    SELECT ARRAY(
        SELECT unnest
        FROM unnest(new_hosts)
        WHERE unnest NOT IN (SELECT fqdn FROM hosts)
    ) INTO hosts_to_add;

    -- Insert hosts from the new list that are not already in the database
    INSERT INTO hosts (fqdn)
    SELECT unnest(hosts_to_add);
END;
$$ LANGUAGE plpgsql;