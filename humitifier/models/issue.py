from pydantic import BaseModel
from typing import Literal

IssueCode = Literal["missing-service-contract"]

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

    slug: IssueCode  # The ID of the issue. Example: "update-kernel"
    title: str  # The title of the issue. Example: "Update kernel"
    description: str  # The description of the issue. Example: "The kernel needs to be updated to 5.10.0-0.bpo.6-amd64"
    severity: Severity  # The severity of the issue. Example: "critical"

    @classmethod
    def create_no_service_contract(cls, hostname: str) -> "Issue":
        return cls(
            slug="missing-service-contract",
            title="Missing Service Contract",
            description=f"No service contract is associated to {hostname}. Create a contract file (`{hostname}.toml`) in the service contracts directory",
            severity="medium",
        )
