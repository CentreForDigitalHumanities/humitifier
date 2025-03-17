from django.urls import reverse

from alerting.models import AlertAcknowledgment
from main.easy_tables import (
    BaseTable,
    BooleanColumn,
    ButtonColumn,
    CompoundColumn,
    MethodColumn,
)


class AlertAcknowledgmentTable(BaseTable):
    class Meta:
        model = AlertAcknowledgment
        columns = [
            "host",
            "short_message",
            "message",
            "acknowledged_by",
            "acknowledged_at",
            "reason",
            "persistent",
            "actions",
        ]
        column_type_overrides = {"persistent": BooleanColumn}

    short_message = MethodColumn("Alert type", method_name="get_short_message")

    message = MethodColumn("Message", method_name="get_message")

    actions = CompoundColumn(
        "Actions",
        columns=[
            ButtonColumn(
                text="Delete",
                button_class="btn btn-danger",
                url=lambda obj: reverse(
                    "alerting:delete_acknowledgment", args=[obj.pk]
                ),
            ),
        ],
    )

    @staticmethod
    def get_short_message(obj: AlertAcknowledgment):
        if generator := obj.get_alert_generator():
            return generator.verbose_name

        return "Unknown"

    @staticmethod
    def get_message(obj: AlertAcknowledgment):
        if alert := obj.get_alert():
            return alert.message

        return "Unknown"
