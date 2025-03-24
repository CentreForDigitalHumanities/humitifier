from datetime import datetime
from typing import TypeVar

from django.core.exceptions import ImproperlyConfigured
from django.db.models import QuerySet

from alerting.backend.data import AlertData, AlertGeneratorType, AnnotatedAlertData
from alerting.models import Alert
from hosts.models import Host
from humitifier_common.artefacts.registry import registry as artefacts_registry
from humitifier_common.scan_data import ScanOutput

T = TypeVar("T")

_BASE_CLASSES = [
    "BaseAlertGenerator",
    "BaseArtefactAlertGenerator",
    "BaseScanAlertGenerator",
]


class AlertGeneratorMetaclass(type):

    def __new__(cls, name, bases, dct):
        new_cls = super().__new__(cls, name, bases, dct)

        # Skip the check if the class is a base FactCollector class
        if name in _BASE_CLASSES:
            return new_cls

        new_cls._creator = name

        if hasattr(new_cls, "artefact") and new_cls.artefact:
            cls._check_if_artefact_exists(new_cls.artefact)

        from .registry import alert_generator_registry

        # We're done, lets add ourselves to the  registry
        alert_generator_registry.register(new_cls)

        return new_cls

    @staticmethod
    def _is_fact_or_metric(obj):
        """
        Determines if the given object is either a fact or a metric by checking the
        presence of specific attributes.

        These attributes should be added by the fact registry;

        :param obj: The object to check for fact or metric attributes.
        :type obj: Any
        :return: Returns `True` if the object has both `__fact_name__` and
            `__fact_type__` attributes, otherwise `False`.
        :rtype: bool
        """
        return hasattr(obj, "__artefact_name__") and hasattr(obj, "__artefact_type__")

    @classmethod
    def _check_if_artefact_exists(cls, artefact):
        """
        Check if a given artefact exists in the registry for a specific class attribute.

        This method verifies whether the provided artefact has a `__artefact_name__`
        attribute and ensures it is registered within the `registry`.
        If the artefact is missing the `__artefact_type__` attribute or is not registered,
        a `ValueError` is raised.

        :param artefact: The object representing the artefact to verify.
        :param attribute: The name of the attribute for which the artefact is being
            checked.
        :type attribute: str
        :raises ValueError: If the artefact lacks the `__artefact_name__` attribute or if
            the artefact is not registered in the `registry`.
        """
        if not cls._is_fact_or_metric(artefact):
            raise ValueError(
                f"Artefact {artefact} does not appear to be a valid fact or metric"
            )

        if not artefacts_registry.get(artefact.__artefact_name__):
            raise ValueError(
                f"Artefact {artefact.__artefact_name__} is not registered in the facts "
                f"registry for {cls.__name__}.artefact"
            )


class BaseAlertGenerator(metaclass=AlertGeneratorMetaclass):
    _type: AlertGeneratorType

    verbose_name: str = None

    def __init__(self):
        self.existing_alerts = Alert.objects.none()

        if self.verbose_name is None:
            raise ImproperlyConfigured("Alert generators must specifiy a verbose name")

    def run(
        self, existing_alerts: QuerySet[Alert]
    ) -> AnnotatedAlertData | list[AnnotatedAlertData]:
        self.existing_alerts = existing_alerts

        alerts = self.generate_alerts()
        if not alerts:
            return []

        if isinstance(alerts, AlertData):
            alerts = [alerts]

        return [
            AnnotatedAlertData(
                creator=self._creator,
                creator_verbose_name=self.verbose_name,
                data=alert,
                existing=self.existing_alerts.filter(
                    custom_identifier=alert.custom_identifier
                ).exists(),
            )
            for alert in alerts
        ]

    def generate_alerts(self) -> AlertData | list[AlertData] | None:
        raise NotImplementedError


class BaseArtefactAlertGenerator(BaseAlertGenerator):
    _type = AlertGeneratorType.ARTEFACT
    artefact: type[T] = None

    def __init__(self, artefact_data: T, scan_date: datetime):
        super().__init__()

        if self.artefact is None:
            raise ImproperlyConfigured("Missing artefact to alert on")

        self.artefact_data = artefact_data
        self.scan_date = scan_date


class BaseScanAlertGenerator(BaseAlertGenerator):
    _type = AlertGeneratorType.SCAN

    def __init__(self, scan_output: ScanOutput):
        super().__init__()
        self.scan_output = scan_output
