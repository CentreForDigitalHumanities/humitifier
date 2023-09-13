from datetime import date, timedelta
from dataclasses import dataclass
from humitifier.props import EndDate, Unknown
from typing import Literal


@dataclass
class ContractExpiration:
    code: Literal["contract-expiration-unknown", "contract-expiration-ok", "contract-expires-soon", "contract-expired"]
    message: str
    severity: Literal[0, 1, 2, 3]

    @classmethod
    def from_host_state(cls, host_state) -> "ContractExpiration":
        end_date = host_state[EndDate]
        if isinstance(end_date, Unknown):
            return cls(code="contract-expiration-unknown", message="No end date specified for contract", severity=1)
        elif end_date > date.today():
            return cls(
                code="contract-expired",
                message=f"This contract is beyond the expiration date ({end_date.isoformat()})",
                severity=3,
            )
        elif end_date > date.today() + timedelta(days=30):
            days_remaining = (date.today() - end_date).days
            return cls(code="contract-expires-soon", message=f"This contract expires in {days_remaining}", severity=2)
        else:
            return cls(code="contract-expiration-ok", message="", severity=0)
