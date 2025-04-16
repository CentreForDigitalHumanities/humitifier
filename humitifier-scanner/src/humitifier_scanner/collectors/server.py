import json
import re
from typing import Literal

import yaml
from datetime import datetime

from humitifier_scanner.collectors import CollectInfo, ShellCollector
from humitifier_scanner.constants import DEB_OS_LIST, RPM_OS_LIST
from humitifier_scanner.executor.linux_shell import LinuxShellExecutor
from humitifier_common.artefacts import (
    HostMeta,
    HostnameCtl,
    IsWordpress,
    PackageList,
    PuppetAgent,
    RebootPolicy,
    Uptime,
    WebHostLocation,
    Webhost,
    WebhostAuth,
    WebhostProxy,
    WebhostRewriteRule,
    Webserver,
)
from humitifier_scanner.utils import os_in_list


class HostMetaFactCollector(ShellCollector):
    fact = HostMeta

    def collect_from_shell(
        self, shell_executor: LinuxShellExecutor, info: CollectInfo
    ) -> HostMeta:
        result = shell_executor.execute("cat /hum/doc/server_facts.json")

        if result.return_code != 0:
            return HostMeta()

        json_str = "\n".join(result.stdout)
        json_args = json.loads(json_str)

        return HostMeta(**json_args)


class WebserverFactCollector(ShellCollector):
    fact = Webserver

    required_facts = [PackageList, HostnameCtl]

    def collect_from_shell(
        self, shell_executor: LinuxShellExecutor, info: CollectInfo
    ) -> Webserver | None:
        hostname_ctl: HostnameCtl = info.required_facts.get(HostnameCtl)
        package_list: PackageList = info.required_facts.get(PackageList)

        webhosts: list[Webhost] = []

        apache_name = self._get_apache_name(hostname_ctl.os)

        if apache_name is not None and self._is_apache_installed(
            apache_name, package_list
        ):
            webhosts += self._process_apache(apache_name, shell_executor)

        return Webserver(hosts=webhosts)

    ##
    ## Apache
    ##

    @staticmethod
    def _get_apache_name(os) -> Literal["apache2", "httpd"] | None:
        apache_name = None
        if os_in_list(os, DEB_OS_LIST):
            apache_name = "apache2"

        if os_in_list(os, RPM_OS_LIST):
            apache_name = "httpd"

        return apache_name

    @staticmethod
    def _is_apache_installed(
        apache_package: Literal["apache2", "httpd"], package_list: PackageList
    ):
        for package in package_list:
            if package.name == apache_package:
                return True

        return False

    @staticmethod
    def _get_apache_file_path(apache_name: str, file: str | None = None):
        if apache_name not in ["apache2", "httpd"]:
            return None

        return f"/etc/{apache_name}/sites-enabled/{file or ""}"

    def _process_apache(
        self, apache_name: str, executor: LinuxShellExecutor
    ) -> list[Webhost]:
        webhosts: list[Webhost] = []

        config_files_cmd = executor.execute(
            ["ls", self._get_apache_file_path(apache_name)]
        )

        config_files = [
            cnf
            for cnf in config_files_cmd.stdout
            # if not cnf.endswith("_redirssl.conf")
        ]

        for config_file in config_files:
            get_contents_cmd = executor.execute(
                ["cat", self._get_apache_file_path(apache_name, config_file)]
            )

            webhosts.append(
                self._parse_apache_file(config_file, get_contents_cmd.stdout)
            )

        return webhosts

    @staticmethod
    def _create_empty_webhost_location() -> WebHostLocation:
        return {
            "document_root": None,
            "auth": None,
            "proxy": None,
            "rewrite_rules": None,
        }

    @staticmethod
    def _create_empty_webhost_auth() -> WebhostAuth:
        return {"type": "", "provider": None}

    def _parse_apache_file(self, filename: str, contents: list[str]) -> Webhost:
        listen_ports: list[int] = []
        document_root: str = ""
        hostname: str = ""
        hostname_aliases: list[str] = []
        rewrite_rules: list[WebhostRewriteRule] = []

        locations: dict[str, WebHostLocation] = {}

        # Parse caches
        rewrite_conditions = []
        current_location: str | None = None

        mode = "default_loop"

        for line in contents:
            line = line.strip()

            if mode == "default_loop":
                if line.startswith("<VirtualHost"):
                    # The -1 strips the trailing >
                    stripped = line[len("<VirtualHost") : -1].strip()
                    host, port = stripped.split(":", 1)
                    try:
                        port = int(port)
                        listen_ports.append(port)
                    except ValueError:
                        pass
                if line.startswith("ServerName"):
                    hostname = line[len("ServerName") :].strip()
                elif line.startswith("ServerAlias"):
                    hostname_aliases.append(line[len("ServerAlias") :].strip())
                elif line.startswith("DocumentRoot"):
                    root = line[len("DocumentRoot") :].strip()

                    if root.startswith('"'):
                        root = root[1:]
                    if root.endswith('"'):
                        root = root[:-1]

                    document_root = root
                elif line.startswith("ProxyPass "):
                    sans_prefix = line[len("ProxyPass ") :].strip()
                    path, proxy = sans_prefix.split(" ", 1)
                    if path not in locations.keys():
                        locations[path] = self._create_empty_webhost_location()

                    # Proxies are in format `proto://endpoint`
                    _type, proxy_endpoint = proxy.split(":", 1)

                    locations[path]["proxy"]: WebhostProxy = {
                        "type": _type,
                        "endpoint": proxy_endpoint,
                    }
                elif line.startswith("RewriteCond"):
                    condition = line[len("RewriteCond") :].strip()
                    rewrite_conditions.append(condition)
                elif line.startswith("RewriteRule"):
                    rule = line[len("RewriteRule") :].strip()
                    rewrite_rules.append(
                        {"conditions": rewrite_conditions, "rule": rule}
                    )

                    # Clear our buffer, as we hit the rewrite rule part
                    rewrite_conditions = []
                elif line.startswith("<Location"):
                    # The -1 strips the trailing >
                    location = line[len("<Location") : -1].strip()
                    if location not in locations:
                        locations[location] = self._create_empty_webhost_location()
                    current_location = location
                    mode = "location_loop"

            elif mode == "location_loop":
                location_obj = locations[current_location]

                if line == "</Location>":
                    current_location = None
                    mode = "default_loop"
                elif line.startswith("AuthType"):
                    stripped = line[len("<AuthType") :].strip()
                    if not location_obj["auth"]:
                        location_obj["auth"] = self._create_empty_webhost_auth()

                    location_obj["auth"]["type"] = stripped
                elif line.startswith("AuthBasicProvider"):
                    stripped = line[len("AuthBasicProvider") :].strip()

                    if not location_obj["auth"]:
                        location_obj["auth"] = self._create_empty_webhost_auth()

                    location_obj["auth"]["provider"] = stripped

        return {
            "listen_ports": listen_ports,
            "webserver": "apache",
            "filename": filename,
            "hostname": hostname,
            "hostname_aliases": hostname_aliases,
            "document_root": document_root,
            "locations": locations,
            "rewrite_rules": rewrite_rules,
        }


class UptimeMetricCollector(ShellCollector):
    metric = Uptime

    def collect_from_shell(
        self, shell_executor: LinuxShellExecutor, info: CollectInfo
    ) -> Uptime:
        result = shell_executor.execute("uptime -s")

        dt = datetime.fromisoformat(result.stdout[0].strip())
        now = datetime.now()

        return Uptime((now - dt).total_seconds())


class PuppetAgentFactCollector(ShellCollector):
    fact = PuppetAgent

    def collect_from_shell(
        self, shell_executor: LinuxShellExecutor, info: CollectInfo
    ) -> PuppetAgent:
        # Running has a None state; this is mostly for if systemctl has a problem
        # systemctl has a tendency to tell you a service is inactive in those cases
        # (which is not the same thing systemd!)
        running = None
        # Assume it's enabled unless otherwise known
        enabled = True
        disabled_message = None

        # Figure out if the systemd-service is running
        service_status_cmd = shell_executor.execute(
            "systemctl status puppet.service &>/dev/null",
            fail_silent=True,
        )
        # Allow for any problem
        if service_status_cmd.return_code == 0:
            running = True
        elif service_status_cmd.return_code == 3:
            running = False

        # Try to retrieve the agent-disabled lock file
        agent_disabled_info_cmd = shell_executor.execute(
            "sudo cat /opt/puppetlabs/puppet/cache/state/agent_disabled.lock",
            # We expect this to fail most of the time, so supress the error log
            fail_silent=True,
        )

        # If we didn't get an error, the file exists and thus the agent is disabled
        if agent_disabled_info_cmd.return_code == 0:
            enabled = False
            # Try and retrieve the contents of the lock-file
            agent_disabled_info = agent_disabled_info_cmd.stdout
            try:
                agent_disabled_info = json.loads("".join(agent_disabled_info))
                disabled_message = agent_disabled_info["disabled_message"]
            except (ValueError, TypeError):
                pass

        # Create our final output object
        output = PuppetAgent(
            enabled=enabled,
            running=running,
            disabled_message=disabled_message,
        )

        # Retrieve the last run report for analysis
        result_report_cmd = shell_executor.execute(
            "sudo cat /opt/puppetlabs/puppet/cache/state/last_run_report.yaml"
        )

        # If we successfully retrieved the report, we can start parsing it
        if result_report_cmd.return_code == 0:

            # The first line contains a ruby object constructor definition; we obviously
            # don't have a ruby object that can be constructed from this, so we skip it.
            # It's not needed to parse the yaml anyway
            yaml_string = "\n".join(result_report_cmd.stdout[1:])
            report_data = yaml.safe_load(yaml_string)

            # Get status data
            status = report_data["status"]
            transaction_completed = report_data["transaction_completed"]
            # The second check is for otherwise interrupted puppet runs
            output.is_failing = status == "failed" or not transaction_completed

            # Some basic covering
            output.last_run = report_data["time"]
            output.environment = report_data["environment"]

            # Extract role and role_variant from the logs
            # We do a 'notify' log line search in the site.pp file which contains the role and role_variant
            # This is a bit of a hack, but we don't have a better way to get this
            # information at this point in time.
            for log_line in report_data["logs"]:
                # We only care about 'notice' log lines originating from the site.pp file
                if (
                    log_line["level"] == "notice"
                    and log_line["file"]
                    and log_line["file"].endswith("site.pp")
                ):
                    message = log_line["message"]

                    # We use a regex to extract the key-value pairs from the log message
                    # The notify message is formatted as follows:
                    # <some text> $key1=value1, $key2=value2, ...
                    # This regex captures these pairs inside two capture groups
                    matches = re.findall(r"\$(\S*?)=(\S*?)[, ]", message)

                    for key, value in matches:
                        if key == "role":
                            output.data_role = value
                        elif key == "role_variant":
                            output.data_role_variant = value

                    # Stop the loop once we've found the right line
                    break

        # Retrieve the classes that were applied during the last run
        classes_cmd = shell_executor.execute(
            "sudo cat /opt/puppetlabs/puppet/cache/state/classes.txt"
        )

        if classes_cmd.return_code == 0:
            classes = set(classes_cmd.stdout)
            output.code_roles = [cls for cls in classes if cls.startswith("roles::")]
            output.profiles = [cls for cls in classes if cls.startswith("profiles::")]

        return output


class IsWordpressFactCollector(ShellCollector):
    fact = IsWordpress

    required_facts = [HostMeta]

    def collect_from_shell(
        self, shell_executor: LinuxShellExecutor, info: CollectInfo
    ) -> IsWordpress:

        host_meta: HostMeta = info.required_facts.get(HostMeta)

        if host_meta.vhosts:
            for vhost in host_meta.vhosts:
                for site, info in vhost.items():
                    result = shell_executor.execute(
                        f"test -f {info.docroot}/wp-config.php",
                        fail_silent=True,  # We expect an error code....
                    )
                    if result.return_code == 0:
                        return IsWordpress(is_wp=True)

        return IsWordpress(is_wp=False)


class RebootPolicyFactCollector(ShellCollector):
    fact = RebootPolicy

    def collect_from_shell(
        self, shell_executor: LinuxShellExecutor, info: CollectInfo
    ) -> RebootPolicy | None:
        result = shell_executor.execute("cat /hum/doc/reboot_policy_facts.json")

        if result.return_code != 0:
            return None

        json_str = "\n".join(result.stdout)
        json_args = json.loads(json_str)

        actual_data = json_args["reboot_policy"]

        output = RebootPolicy(
            configured=actual_data["ensure"] == "present",
        )

        if "enable" in actual_data:
            output.enabled = actual_data["enable"]

        for item in ["cron_minute", "cron_hour", "cron_monthday"]:
            if item in actual_data:
                val = str(actual_data.get(item))
                setattr(output, item, val)

        return output
