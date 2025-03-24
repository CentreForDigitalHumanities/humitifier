from enum import Enum

from pydantic import BaseModel


class AlertGeneratorType(Enum):
    ARTEFACT = "Artefact"
    SCAN = "Scan"


class AlertData(BaseModel):
    severity: str
    message: str
    fatal: bool = False
    custom_identifier: str | None = None
    can_acknowledge: bool = True


class AnnotatedAlertData(BaseModel):
    creator: str
    creator_verbose_name: str
    data: AlertData
    existing: bool


class GeneratedAlerts(BaseModel):
    host: str
    alerts: list[AnnotatedAlertData]
