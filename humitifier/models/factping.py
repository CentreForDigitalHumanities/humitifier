from humitifier import facts as infra_facts
from pydantic import BaseModel


class FactPing(BaseModel):
    users: list[infra_facts.User] | None
    groups: list[infra_facts.Group] | None
    hostnamectl: infra_facts.HostnameCtl | None
    memory: infra_facts.Memory | None
    blocks: list[infra_facts.Block] | None
    uptime: infra_facts.Uptime | None
    packages: list[infra_facts.Package] | None

    @classmethod
    def from_facts(cls, facts=list[infra_facts.FactData]) -> "FactPing":
        kwargs = {
            "users": None,
            "groups": None,
            "hostnamectl": None,
            "memory": None,
            "blocks": None,
            "uptime": None,
            "packages": None,
        }
        for fact in facts:
            match fact.__class__:
                case infra_facts.HostnameCtl:
                    kwargs["hostnamectl"] = fact
                case infra_facts.Memory:
                    kwargs["memory"] = fact
                case infra_facts.Uptime:
                    kwargs["uptime"] = fact
                case list:
                    for f in fact:
                        match f.__class__:
                            case infra_facts.User:
                                kwargs["users"] = kwargs["users"] or []
                                kwargs["users"].append(f)
                            case infra_facts.Group:
                                kwargs["groups"] = kwargs["groups"] or []
                                kwargs["groups"].append(f)
                            case infra_facts.Package:
                                kwargs["packages"] = kwargs["packages"] or []
                                kwargs["packages"].append(f)
                            case infra_facts.Block:
                                kwargs["blocks"] = kwargs["blocks"] or []
                                kwargs["blocks"].append(f)
        return cls(**kwargs)

    @classmethod
    def factping_kv(cls, facts=list[tuple[str, infra_facts.FactData]]) -> dict[str, "FactPing"]:
        unique_hosts = {fact[0] for fact in facts}
        return {host_fqdn: cls.from_facts([fact_data for fact_fqdn, fact_data in facts if fact_fqdn == host_fqdn]) for host_fqdn in unique_hosts}
    

