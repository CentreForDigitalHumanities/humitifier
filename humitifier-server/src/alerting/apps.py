from django.apps import AppConfig


class AlertingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "alerting"

    def ready(self):
        import alerting.signals  # NoQA
        import alerting.alerts  # NoQA
