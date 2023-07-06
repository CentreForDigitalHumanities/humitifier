from pydantic import BaseModel
from typing import Literal


Severity = Literal[
    "critical",
    "high",
    "medium",
    "low",
    "informational",
]


class Issue(BaseModel):
    """
    An issue
    """

    slug: str  # The ID of the issue. Example: "update-kernel"
    title: str  # The title of the issue. Example: "Update kernel"
    description: str  # The description of the issue. Example: "The kernel needs to be updated to 5.10.0-0.bpo.6-amd64"
    severity: Severity  # The severity of the issue. Example: "critical"
