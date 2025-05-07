import json
import re
from typing import Literal

import yaml
from datetime import datetime

from .backend import CollectInfo, ShellCollector, FileCollector
from humitifier_scanner.constants import DEB_OS_LIST, RPM_OS_LIST
from humitifier_scanner.executor.linux_shell import LinuxShellExecutor
from humitifier_scanner.executor.linux_files import LinuxFilesExecutor
from humitifier_common.artefacts import (
    HostMeta,
    HostnameCtl,
    IsWordpress,
    PackageList,
    PuppetAgent,
    RebootPolicy,
    Uptime,
    Webhost,
    Webserver,
)
from humitifier_scanner.parsers.apache import ApacheConfigParser
from humitifier_scanner.parsers.nginx import NginxConfigParser
from humitifier_scanner.utils import os_in_list


class HostMetaFactCollector(FileCollector):
    fact = HostMeta

    def collect_from_files(
        self, files_executor: LinuxFilesExecutor, info: CollectInfo
    ) -> HostMeta:
        with files_executor.open("/hum/doc/server_facts.json") as file:
            json_args = json.loads(file.read())

            return HostMeta(**json_args)


class WebserverFactCollector(FileCollector):
    fact = Webserver

    required_facts = [PackageList, HostnameCtl]

    def collect_from_files(
        self, files_executor: LinuxFilesExecutor, info: CollectInfo
    ) -> Webserver | None:
        hostname_ctl: HostnameCtl = info.required_facts.get(HostnameCtl)
        package_list: PackageList = info.required_facts.get(PackageList)

        webhosts: list[Webhost] = []

        apache_name = self._get_apache_name(hostname_ctl.os)
        if apache_name is not None and self._is_webserver_installed(
            apache_name, package_list
        ):
            webhosts += self._process_apache(apache_name, files_executor)

        if self._is_webserver_installed("nginx", package_list):
            webhosts += self._process_nginx(files_executor)

        return Webserver(hosts=webhosts)

    ##
    ## Generic
    ##

    @staticmethod
    def _is_webserver_installed(
        webserver_package: Literal["apache2", "httpd", "nginx"],
        package_list: PackageList,
    ):
        for package in package_list:
            if package.name == webserver_package:
                return True

        return False

    ##
    ## NGINX
    ##

    @staticmethod
    def _get_nginx_file_path(file: str):
        return

    @staticmethod
    def _process_nginx(executor: LinuxFilesExecutor) -> list[Webhost]:
        webhosts: list[Webhost] = []

        config_files = executor.list_dir("/etc/nginx/sites-enabled/")

        for config_file in config_files:
            webhosts += NginxConfigParser.parse(config_file, executor)

        return webhosts

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
    def _get_apache_file_path(apache_name: str, file: str | None = None):
        if apache_name not in ["apache2", "httpd"]:
            return None

        return f"/etc/{apache_name}/sites-enabled/{file or ""}"

    def _process_apache(
        self, apache_name: str, executor: LinuxFilesExecutor
    ) -> list[Webhost]:
        webhosts: list[Webhost] = []

        config_files = executor.list_dir(self._get_apache_file_path(apache_name))

        for config_file in config_files:
            webhosts.append(ApacheConfigParser.parse(config_file, executor))

        return webhosts


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


class RebootPolicyFactCollector(FileCollector):
    fact = RebootPolicy

    def collect_from_files(
        self, files_executor: LinuxFilesExecutor, info: CollectInfo
    ) -> RebootPolicy | None:

        with files_executor.open("/hum/doc/reboot_policy_facts.json") as file:
            json_args = json.loads(file.read())

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
