from dataclasses import asdict
from jinja2 import Template
from . import properties as props

BlockLine = Template(
    "{{name}}        {{size_mb}}  {{used_mb}}     {{available_mb}}  {{use_percent}}% {{mount}}"
)
BlocksHeader = "Filesystem     1M-blocks  Used Available Use% Mounted on"
    
HostnameCtl = Template(
    "   Static hostname: {{hostname}}\n"
    "    Virtualization: {{virtualization}}\n"
    "  Operating System: {{os}}\n"
    "            Kernel: {{kernel}}\n"
    "      Architecture: x86-64\n"
)


Memory = Template(
    "total used free shared buff/cache available\n"
    "Mem: {{total_mb}} {{used_mb}} {{free_mb}} 0 0\n"
    "Swap: {{swap_total_mb}} {{swap_used_mb}} {{swap_free_mb}}\n"
)
    
GroupLine = Template(
    "{{name}}:x:{{gid}}:{{users}}"
)

PackageLine = Template("{{name}}\t{{version}}")

UptimeLine = Template("up {{days}} days, {{hours}} hours, {{minutes}} minutes")

UserLine = Template(
    "{{name}}:x:{{uid}}:{{gid}}:{{gecos}}:{{home}}:{{shell}}"
)

def fake_blocks_stdout(*args) -> list[str]:
    blocks = props.fake_blocks(*args)
    return [BlocksHeader] + [BlockLine.render(**asdict(block)) for block in blocks]

def fake_hostnamectl_stdout(**kwargs) -> list[str]:
    ctl = props.fake_hostnamectl(**kwargs)
    return HostnameCtl.render(**asdict(ctl)).splitlines()

def fake_memory_stdout(**kwargs) -> list[str]:
    memory = props.fake_memory(**kwargs)
    return Memory.render(**asdict(memory)).splitlines()

def fake_package_list_stdout(*args) -> list[str]:
    packages = props.fake_package_list(*args)
    return [PackageLine.render(**asdict(package)) for package in packages]

def fake_uptime_stdout(**kwargs) -> list[str]:
    uptime = props.fake_uptime(**kwargs)
    hours = uptime.seconds // 3600
    minutes = (uptime.seconds % 3600) // 60
    return [UptimeLine.render(days=uptime.days, hours=hours, minutes=minutes)]

def fake_groups_stdout(*args) -> list[str]:
    groups = props.fake_groups(*args)
    return [GroupLine.render(**asdict(group)) for group in groups]

def fake_users_stdout(*args) -> list[str]:
    users = props.fake_users(*args)
    return [UserLine.render(**asdict(user)) for user in users]