from celery import shared_task
from django.db.models import Q

from humitifier_server.celery.task_names import (
    API_CLEAR_EXPIRED_TOKENS,
    API_DATASOURCE_SYNC,
)


@shared_task(name=API_CLEAR_EXPIRED_TOKENS)
def clear_expired_tokens():
    from oauth2_provider.models import clear_expired

    clear_expired()


@shared_task(name=API_DATASOURCE_SYNC)
def datasource_sync(hosts: list[dict], data_source_id: int):
    from hosts.models import DataSource, Host

    data_source = DataSource.objects.get(pk=data_source_id)

    # Transform the list of hosts into a dict with the fqdn as key. Simplifies logic later on
    hosts_dict = {host["fqdn"]: host for host in hosts}

    # Get all hosts that we already know about and are either owned by this data source or currently unowned
    existing_hosts = Host.objects.filter(
        fqdn__in=hosts_dict.keys(),
    ).filter(Q(data_source=data_source) | Q(data_source=None))

    # Find any hosts that are not in our database yet
    new_hosts = [
        fqdn
        for fqdn in hosts_dict.keys()
        if fqdn not in existing_hosts.values_list("fqdn", flat=True)
    ]

    # Find any hosts that we know of, but are not provided by our API client
    # These hosts should be archived
    removed_hosts = Host.objects.filter(
        data_source=data_source,
    ).exclude(
        fqdn__in=hosts_dict.keys(),
    )

    for removed_host in removed_hosts:
        if not removed_host.archived:
            removed_host.archive()

    # Then, let's update our existing hosts
    for host in existing_hosts:
        new_data = hosts_dict.get(host.fqdn)

        # Update our ownership info
        host.department = new_data.get("department", host.department)
        host.customer = new_data.get("customer", host.customer)
        host.contact = new_data.get("contact", host.contact)

        # Update other static info
        host.has_tofu_config = new_data.get("has_tofu_config", host.has_tofu_config)
        host.otap_stage = new_data.get("otap_stage", host.otap_stage)
        host.billable = new_data.get("billable", host.billable)
        host.asset_tag = new_data.get("asset_tag", host.asset_tag)

        # If this host is unclaimed, we set the data_source attr to claim it
        if host.data_source is None:
            host.data_source = data_source

        host.save()
        host.set_powerstate(offline=new_data.get("offline"))

        if host.archived:
            host.unarchive()

    # Lastly, create new hosts
    for fqdn in new_hosts:
        new_data = hosts_dict.get(fqdn)

        data = {
            "fqdn": fqdn,
            "data_source": data_source,
            "department": new_data.get("department"),
            "customer": new_data.get("customer"),
            "contact": new_data.get("contact"),
            "has_tofu_config": new_data.get("has_tofu_config"),
            "otap_stage": new_data.get("otap_stage"),
            "billable": new_data.get("billable"),
        }

        host = Host.objects.create(**data)
        host.set_powerstate(offline=new_data.get("offline"))
