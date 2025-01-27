import dataclasses
import uuid
from datetime import datetime
from functools import cached_property
from typing import get_args

from django.db import models
from django.db.models import Case, F, Value, When
from django.utils import timezone
from django.utils.safestring import mark_safe

from api.models import OAuth2Application
from humitifier_common.artefacts.registry.registry import (
    registry as artefact_registry,
)
from humitifier_common.scan_data import ScanOutput
from humitifier_server.logger import logger
from main.models import User
from main.templatetags.strip_quotes import strip_quotes


@dataclasses.dataclass
class ScanData:
    version: int
    scan_date: datetime
    raw_data: dict

    @classmethod
    def from_raw_scan(cls, raw_scan: dict, created: datetime) -> "ScanData":
        # Version 1 doesn't have a version field, so we default to one and
        # override with any specified version if available
        version = 1
        if "version" in raw_scan:
            version = raw_scan["version"]

        return cls(version=version, raw_data=raw_scan, scan_date=created)

    @cached_property
    def parsed_data(self) -> ScanOutput | None:
        # Not supported by version 1 of the scan output format :(
        if self.version == 1:
            logger.debug(
                "Someone tried to get a parsed scan output from a v1 scan. This is not supported or possible."
            )
            return None

        output = ScanOutput(**self.raw_data)

        output.facts = {
            name: self._parse_artefact(name, data)
            for name, data in output.facts.items()
        }
        output.metrics = {
            name: self._parse_artefact(name, data)
            for name, data in output.metrics.items()
        }

        return output

    @staticmethod
    def _parse_artefact(artefact_name, data):
        artefact = artefact_registry.get(artefact_name)

        if isinstance(data, dict):
            return artefact(**data)

        if isinstance(data, list):
            inner_type = get_args(artefact.__orig_bases__[0])[0]
            if inner_type:
                return artefact([inner_type(**datum) for datum in data])
            return artefact(data)

        return artefact(data) if data else None


class DataSourceType(models.TextChoices):
    API = ("api", "API Sync")
    MANUAL = ("manual", "Manual entry")


class ScanScheduling(models.TextChoices):
    MANUAL = ("manual", "Manual/host initiated scanning")
    SCHEDULED = ("scheduled", "Scheduled scanning")


class AlertLevel(models.TextChoices):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(models.TextChoices):
    OUTDATED_OS = "Outdated OS"
    FACT_ERROR = "Has fact error"
    DISABLED_PUPPET = "Puppet agent disabled"


def _json_value(field: str):
    """
    Fields derived from JSON data are a bit tricky. If the field is null,
    PSQL will derive 'null' as a string, which is not the same as None.
    (Also, somehow 'null' as a string seems to be uploaded as well).

    So, we do a small case to transform those 'null' strings into actual nulls.
    :param field:
    :return:
    """
    return Case(
        When(**{field: "null", "then": Value(None)}),
        When(**{field: None, "then": Value(None)}),
        default=F(field),
    )


class DatasSourceManager(models.Manager):

    def get_for_user(self, user: User):
        if user.is_anonymous:
            return self.get_queryset().none()

        if user.is_superuser:
            return self.get_queryset()

        if user.access_profiles.exists():
            return self.get_queryset().filter(
                id__in=user.access_profiles.values_list("data_sources", flat=True)
            )

        # When a non-superuser has no access profile, THEY GET NOTHING
        # They lose! Good day sir!
        return self.get_queryset().none()

    def get_for_application(self, application: OAuth2Application):
        if application.access_profile is None:
            return self.get_queryset().none()

        if "system" not in application.allowed_scopes:
            return self.get_queryset().none()

        return self.get_queryset().filter(
            id__in=application.access_profile.data_sources.all()
        )


class DataSource(models.Model):
    class Meta:
        ordering = ["name"]

    objects = DatasSourceManager()

    identifier = models.UUIDField(
        null=False,
        unique=True,
        default=uuid.uuid4,
    )

    name = models.CharField(max_length=255)

    source_type = models.CharField(
        max_length=255, choices=DataSourceType.choices, default=DataSourceType.MANUAL
    )

    scan_scheduling = models.CharField(
        max_length=255, choices=ScanScheduling.choices, default=ScanScheduling.SCHEDULED
    )

    def __str__(self):
        return self.name


class HostManager(models.Manager):

    def get_for_user(self, user: User):
        if user.is_anonymous:
            return self.get_queryset().none()

        if user.is_superuser:
            return self.get_queryset()

        if user.access_profiles.exists():
            return self.get_queryset().filter(customer__in=user.customers_for_filter)

        # When a non-superuser has no access profile, THEY GET NOTHING
        # They lose! Good day sir!
        return self.get_queryset().none()

    def get_for_application(self, application: OAuth2Application):
        if application.access_profile is None:
            return self.get_queryset().none()

        return self.get_queryset().filter(
            customer__in=application.access_profile.customers_for_filter
        )


class Host(models.Model):
    class Meta:
        ordering = ["fqdn"]

    objects = HostManager()

    fqdn = models.CharField("Hostname", max_length=255)

    last_scan_cache = models.JSONField(
        null=True,
    )

    last_scan_date = models.DateTimeField(
        null=True,
    )

    created_at = models.DateTimeField(
        "Registered",
        auto_now_add=True,
    )

    protected = models.BooleanField(default=False)

    archived = models.BooleanField(default=False)

    archival_date = models.DateTimeField(null=True)

    data_source = models.ForeignKey(
        DataSource,
        verbose_name="Data source",
        help_text="The data source for this host",
        on_delete=models.SET_NULL,
        related_name="hosts",
        null=True,
    )

    ##
    ## Static host info
    ##

    has_tofu_config = models.BooleanField(
        default=False,
    )

    otap_stage = models.CharField(
        null=True,
        blank=True,
    )

    department = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    customer = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    contact = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    ##
    ## Generated fields
    ## These fields are derived from the last scan cache, and are generated
    ## by the database itself. THis way, we have a very performant way
    ## to filter on these values
    ##

    os = models.GeneratedField(
        expression=_json_value("last_scan_cache__HostnameCtl__os"),
        output_field=models.CharField(max_length=255),
        db_persist=True,
    )

    ##
    ## Methods
    ##

    def add_scan(
        self, scan_data, *, cache_scan: bool = True, generate_alerts: bool = True
    ):
        if self.archived:
            return None

        scan = Scan(host=self, data=scan_data)
        scan.save()

        if cache_scan:
            self.last_scan_cache = scan_data
            self.last_scan_date = scan.created_at
            self.save()

        if generate_alerts:
            from hosts import alerts

            alerts.generate_alerts(scan_data, self)

        return scan

    def get_scan_object(self) -> ScanData:
        return ScanData.from_raw_scan(self.last_scan_cache, self.last_scan_date)

    def regenerate_alerts(self):
        from hosts import alerts

        alerts.generate_alerts(self.last_scan_cache, self)

    ##
    ## Properties
    ##

    @property
    def num_critical_alerts(self):
        return self._get_alerts_for_level(AlertLevel.CRITICAL, count=True)

    @property
    def num_warning_alerts(self):
        return self._get_alerts_for_level(AlertLevel.WARNING, count=True)

    @property
    def num_info_alerts(self):
        return self._get_alerts_for_level(AlertLevel.INFO, count=True)

    def _get_alerts_for_level(self, level, count=False):
        # Use the prefetched objects if they are available
        # It's not quicker for a single query, but it is for multiple queries
        # (Read: the list page)
        if "alerts" in self._prefetched_objects_cache:
            alerts = [alert for alert in self.alerts.all() if (alert.level == level)]
            if count:
                return len(alerts)
            return alerts

        qs = self.alerts.filter(level=level)

        if count:
            return qs.count()
        return qs

    @property
    def can_manually_edit(self):
        # If it's unclaimed, it's fair game
        if not self.data_source:
            return True

        return self.data_source.source_type == DataSourceType.MANUAL

    @property
    def can_schedule_scan(self):
        # We have no idea!
        if not self.data_source:
            return False

        return self.data_source.scan_scheduling == ScanScheduling.SCHEDULED

    ##
    ## Display methods
    ##

    def get_department_display(self):
        if not self.department:
            return mark_safe("<span class='italic'>Unknown</span>")
        return strip_quotes(self.department)

    def get_customer_display(self):
        if not self.customer:
            return mark_safe("<span class='italic'>Unknown</span>")
        return strip_quotes(self.customer)

    def get_contact_display(self):
        if not self.contact:
            return mark_safe("<span class='italic'>Unknown</span>")
        return strip_quotes(self.contact)

    def get_os_display(self):
        if not self.os:
            return mark_safe("<span class='italic'>Unknown</span>")
        return strip_quotes(self.os)

    @property
    def archived_string(self):
        if self.archived:
            date = self.archival_date.strftime("%Y-%m-%d %H:%M")
            return f"This server was archived on {date}"
        return ""

    def switch_archived_status(self):
        """
        Toggles the archived status of the instance. If the instance is currently archived,
        it will be unarchived. Otherwise, it will be archived.

        :raises Exception: If any error occurs during the archive or unarchive process.
        :return: None
        """
        if self.archived:
            self.unarchive()
        else:
            self.archive()

    def archive(self):
        """
        Marks the object as archived, sets the archival date to the current date and
        time, saves the object state, and deletes all associated alerts from the
        database.

        :return: None
        """
        self.archived = True
        self.archival_date = timezone.now()
        self.save()
        self.alerts.all().delete()

    def unarchive(self):
        """
        Restores the item by setting its archived status to False, clearing its archival
        date, saving the current state, and regenerating relevant alerts.

        :raises ValueError: If the operation cannot complete due to improper state or
            logic conflict.
        :return: None
        """
        self.archived = False
        self.archival_date = None
        self.save()
        self.regenerate_alerts()

    def __str__(self):
        return self.fqdn

    def __repr__(self):
        return f"<Host: {self.fqdn}>"


class Scan(models.Model):
    class Meta:
        ordering = ["-created_at"]

    host = models.ForeignKey(Host, on_delete=models.CASCADE, related_name="scans")

    data = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)

    def get_scan_object(self) -> ScanData:
        return ScanData.from_raw_scan(self.data, self.created_at)


class AlertManager(models.Manager):

    def get_for_user(self, user: User):
        if user.is_anonymous:
            return self.get_queryset().none()

        if user.is_superuser:
            return self.get_queryset()

        if user.access_profiles.exists():
            return self.get_queryset().filter(
                host__customer__in=user.customers_for_filter
            )

        # When a non-superuser has no access profile, THEY GET NOTHING
        # They lose! Good day sir!
        return self.get_queryset().none()


class Alert(models.Model):
    class Meta:
        ordering = ["-created_at"]

    objects = AlertManager()

    host = models.ForeignKey(Host, on_delete=models.CASCADE, related_name="alerts")

    level = models.CharField(max_length=255, choices=AlertLevel.choices)

    type = models.CharField(max_length=255, choices=AlertType.choices)

    message = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __repr__(self):
        return f"<Alert: {self.type} for {self.host.fqdn}>"

    def __str__(self):
        return self.message
