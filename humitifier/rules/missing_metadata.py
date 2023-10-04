from dataclasses import dataclass
from humitifier.props import Department, EndDate, Owner, Purpose, Unknown
from typing import Literal


@dataclass
class MissingMetadata:
    code: Literal["missing-meta-properties", "no-missing-meta-properties"]
    message: str
    severity: Literal[0, 2]

    @classmethod
    @property
    def alias(cls) -> str:
        return "missing_metadata_rule"

    @classmethod
    def from_host_state(cls, host_state) -> "MissingMetadata":
        value_map = {
            Department.alias: host_state[Department],
            EndDate.alias: host_state[EndDate],
            Owner.alias: host_state[Owner],
            Purpose.alias: host_state[Purpose],
        }
        unknowns = [k for k, v in value_map.items() if isinstance(v, Unknown)]
        if unknowns:
            return cls(
                code="missing-meta-properties",
                message=f"Definition is missing the following metadata: {unknowns}",
                severity=2,
            )
        else:
            return cls(code="no-missing-meta-properties", message="All desired metadata is present", severity=0)
