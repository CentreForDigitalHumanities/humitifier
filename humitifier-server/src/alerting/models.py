from django.db import models

from alerting.backend.registry import alert_generator_registry
from main.models import User


class AlertSeverity(models.TextChoices):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


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
        unique_together = ("host", "_creator", "custom_identifier")

    objects = AlertManager()

    ##
    ## Identifiers
    ##

    # Link against a host
    host = models.ForeignKey(
        "hosts.Host",
        on_delete=models.CASCADE,
        related_name="alerts",
    )

    # Link against an Alert generator
    _creator = models.CharField(
        max_length=255,
    )

    custom_identifier = models.CharField(
        verbose_name="Custom identifier",
        help_text="Used during alert-checking to differentiate between instances of an alert",
        max_length=255,
        null=True,
        blank=True,
    )

    ##
    ## Info
    ##

    short_message = models.CharField(
        verbose_name="Short message",
        max_length=255,
    )

    message = models.TextField(
        verbose_name="Full message",
        null=True,
        blank=True,
    )

    severity = models.CharField(
        verbose_name="Severity",
        max_length=50,
        choices=AlertSeverity.choices,
    )

    created_at = models.DateTimeField(
        verbose_name="First occurrence",
        auto_now_add=True,
    )

    last_seen_at = models.DateTimeField(
        verbose_name="Last occurrence",
        null=True,
        blank=True,
    )

    _notified = models.BooleanField(
        default=False,
    )

    # To be set by creator, internal use
    _can_acknowledge = models.BooleanField(
        default=True,
    )

    def get_acknowledgment(self):
        # The attr will not exist if no link exists
        # Thanks Django, for this amazing behavior
        if hasattr(self, "acknowledgement"):
            return self.acknowledgement

        acknowledgments = AlertAcknowledgment.objects.filter(
            host=self.host,
            _creator=self._creator,
            custom_identifier=self.custom_identifier,
        )

        if acknowledgments.exists():
            return acknowledgments.get()

        return None

    @property
    def can_acknowledge(self):
        return self._can_acknowledge


class AlertAcknowledgment(models.Model):
    class Meta:
        unique_together = ("host", "_creator", "custom_identifier")

    ##
    ## Identifiers
    ##

    # Mostly for easy of use
    _alert = models.OneToOneField(
        Alert,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="acknowledgement",
    )

    # Link against a host
    host = models.ForeignKey(
        "hosts.Host",
        on_delete=models.CASCADE,
        related_name="alert_acknowledgements",
    )

    # Link against an Alert generator
    _creator = models.CharField(
        max_length=255,
    )

    custom_identifier = models.CharField(
        verbose_name="Custom identifier",
        help_text="Used during alert-checking to differentiate between instances of an alert",
        max_length=255,
        null=True,
        blank=True,
    )

    ##
    ## Info
    ##

    acknowledged_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    acknowledged_at = models.DateTimeField(
        auto_now_add=True,
    )

    reason = models.TextField()

    persistent = models.BooleanField(
        "Persistent acknowledgement",
        help_text="If checked, this alert will persist after the original alert "
        "condition disappears, suppressing any alerts in perpetuity",
        default=False,
    )

    ##
    ## Methods
    ##

    def get_alert(self):
        # The attr will not exist if no link exists
        # Thanks Django, for this amazing behavior
        if hasattr(self, "_alert"):
            return self._alert

        alerts = Alert.objects.filter(
            _creator=self._creator,
            host=self.host,
            custom_identifier=self.custom_identifier,
        )

        if alerts.exists():
            return alerts.get()

        return None

    def get_alert_generator(self):
        return alert_generator_registry.get(self._creator)
