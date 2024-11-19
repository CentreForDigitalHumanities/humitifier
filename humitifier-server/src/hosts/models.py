from django.db import models
from django.db.models import Case, F, Value, When
from django.utils.safestring import mark_safe

from api.models import OAuth2Application
from main.models import User
from main.templatetags.strip_quotes import strip_quotes


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


class HostManager(models.Manager):

    def get_for_user(self, user: User):
        if user.is_anonymous:
            return self.get_queryset().none()

        if user.is_superuser:
            return self.get_queryset()

        if user.access_profiles.exists():
            return self.get_queryset().filter(
                department__in=user.departments_for_filter
            )

        # When a non-superuser has no access profile, THEY GET NOTHING
        # They lose! Good day sir!
        return self.get_queryset().none()

    def get_for_application(self, application: OAuth2Application):
        if application.access_profile is None:
            return self.get_queryset().none()

        return self.get_queryset().filter(
            department__in=application.access_profile.departments_for_filter
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

    ##
    ## Generated fields
    ## These fields are derived from the last scan cache, and are generated
    ## by the database itself. THis way, we have a very performant way
    ## to filter on these values
    ##

    department = models.GeneratedField(
        expression=_json_value("last_scan_cache__HostMeta__department"),
        output_field=models.CharField(max_length=255),
        db_persist=True,
    )

    contact = models.GeneratedField(
        expression=_json_value("last_scan_cache__HostMeta__contact"),
        output_field=models.CharField(max_length=255),
        db_persist=True,
    )

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

    ##
    ## Display methods
    ##

    def get_department_display(self):
        if not self.department:
            return mark_safe("<span class='italic'>Unknown</span>")
        return strip_quotes(self.department)

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


class AlertManager(models.Manager):

    def get_for_user(self, user: User):
        if user.is_anonymous:
            return self.get_queryset().none()

        if user.is_superuser:
            return self.get_queryset()

        if user.access_profiles.exists():
            return self.get_queryset().filter(
                host__department__in=user.departments_for_filter
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
