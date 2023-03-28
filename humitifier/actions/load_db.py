import os
import toml
import json
from datetime import timedelta, date
from humitifier.models import Server, Package, ServiceContract, Person


def _load_packages(packages_dict: dict) -> tuple[str, list[Package]]:
    packages = [Package(name=item["name"], version=item["version"]) for item in packages_dict["value"]["packages"]]
    return packages_dict["target"], packages


def _load_server(
    server_dict: dict, contracts: dict[str, ServiceContract], packages: dict[str, list[Package]]
) -> Server:
    data = server_dict["value"]
    slug = data["hostname"]
    return Server(
        name=slug,
        is_virtual=data["is_virtual"],
        cpu_total=data["processorcount"],
        uptime=timedelta(seconds=data["uptime_seconds"]),
        ip_address=data["ipaddress"],
        memory_total=data["memorysize_mb"],
        memory_usage=data["memorysize_mb"] - data["memoryfree_mb"],
        os=f"{data['operatingsystem']} {data['operatingsystemrelease']}",
        reboot_required=False,
        nfs_shares=[],
        webdav_shares=[],
        groups=[],
        users=[],
        service_contract=contracts.get(slug),
        packages=packages.get(server_dict["target"], []),
        cpu_usage=0,
        local_storage_total=data["blockdevice_sda_size"] / 1024 / 1024 / 1024,
        local_storage_usage=0,
    )


def _load_person(person_dict: dict) -> Person:
    return Person(
        name=person_dict["name"],
        email=person_dict["email"],
        department=person_dict.get("department"),
        role=person_dict.get("role"),
        notes=person_dict.get("notes"),
    )


def _load_contract(path: str) -> tuple[str, ServiceContract]:
    with open(path) as f:
        data = toml.load(f)
    slug = os.path.basename(path).replace(".toml", "")

    creation_date = date.fromisoformat(data["contract"]["creation_date"])
    expiry_date = date.fromisoformat(data["contract"]["expiry_date"])
    contract = ServiceContract(
        entity=data["contract"]["entity"],
        owner=_load_person(data["contract"]["owner"]),
        creation_date=creation_date,
        expiry_date=expiry_date,
        purpose=data["contract"]["purpose"],
        people=[_load_person(p) for p in data["people"]],
    )
    return slug, contract


def main(boltscan: str, contract_dir: str) -> list[Server]:
    with open(boltscan) as f:
        boltdata = json.load(f)
    contract_files = [f"{contract_dir}/{f}" for f in os.listdir(contract_dir) if f.endswith(".toml")]
    contracts = (_load_contract(f) for f in contract_files)
    contracts = {k: v for k, v in contracts}
    package_pairs = (_load_packages(pd) for pd in boltdata[0]["packages"])
    package_pairs = {k: v for k, v in package_pairs}
    servers = [_load_server(sd, contracts, package_pairs) for sd in boltdata[1]["facts"]]
    return servers
