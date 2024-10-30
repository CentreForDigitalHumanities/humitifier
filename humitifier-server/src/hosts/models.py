from django.db import models
from django.db.models import Case, F, Value, When
from django.utils.safestring import mark_safe

from main.templatetags.strip_quotes import strip_quotes


class AlertLevel(models.TextChoices):
    INFO = 'info'
    WARNING = 'warning'
    CRITICAL = 'critical'


class AlertType(models.TextChoices):
    OUTDATED_OS = 'Outdated OS'
    FACT_ERROR = 'Has fact error'
    DISABLED_PUPPET = 'Puppet agent disabled'


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
        When(
            **{field: 'null', 'then': Value(None)}
        ),
        When(
            **{field: None, 'then': Value(None)}
        ),
        default=F(field),
    )


class HostManager(models.Manager):

    def get_for_user(self, user):
        # TODO: implement this when we have user support
        return self.get_queryset()


class Host(models.Model):
    class Meta:
        ordering = ['fqdn']

    objects = HostManager()

    fqdn = models.CharField(max_length=255)

    last_scan_cache = models.JSONField(
        null=True,
    )

    last_scan_date = models.DateTimeField(
        null=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    protected = models.BooleanField(default=False)

    ##
    ## Generated fields
    ## These fields are derived from the last scan cache, and are generated
    ## by the database itself. THis way, we have a very performant way
    ## to filter on these values
    ##

    department = models.GeneratedField(
        expression=_json_value('last_scan_cache__HostMeta__department'),
        output_field=models.CharField(max_length=255),
        db_persist=True,
    )

    contact = models.GeneratedField(
        expression=_json_value('last_scan_cache__HostMeta__contact'),
        output_field=models.CharField(max_length=255),
        db_persist=True,
    )

    os = models.GeneratedField(
        expression=_json_value('last_scan_cache__HostnameCtl__os'),
        output_field=models.CharField(max_length=255),
        db_persist=True,
    )

    ##
    ## Methods
    ##

    def add_scan(
            self,
            scan_data,
            *,
            cache_scan: bool = True,
            generate_alerts: bool = True
    ):
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

    ##
    ## Properties
    ##

    @property
    def num_critical_alerts(self):
        return self.alerts.filter(level=AlertLevel.CRITICAL).count()

    @property
    def num_warning_alerts(self):
        return self.alerts.filter(level=AlertLevel.WARNING).count()

    @property
    def num_info_alerts(self):
        return self.alerts.filter(level=AlertLevel.INFO).count()

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

    def __str__(self):
        return self.fqdn

    def __repr__(self):
        return f"<Host: {self.fqdn}>"


class Scan(models.Model):
    class Meta:
        ordering = ['-created_at']

    host = models.ForeignKey(Host, on_delete=models.CASCADE, related_name='scans')

    data = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)


class AlertManager(models.Manager):

        def get_for_user(self, user):
            # TODO: implement this when we have user support
            return self.get_queryset()


class Alert(models.Model):
    class Meta:
        ordering = ['-created_at']

    objects = AlertManager()

    host = models.ForeignKey(Host, on_delete=models.CASCADE, related_name='alerts')

    level = models.CharField(max_length=255, choices=AlertLevel.choices)

    type = models.CharField(max_length=255, choices=AlertType.choices)

    message = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __repr__(self):
        return f"<Alert: {self.type} for {self.host.fqdn}>"

    def __str__(self):
        return self.message
