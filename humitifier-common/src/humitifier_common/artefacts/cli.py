"""For artefacts not usually collected for storing in the server DB, but
for scans done manually.
"""

from pydantic import BaseModel

from humitifier_common.artefacts.groups import CLI
from humitifier_common.artefacts.registry import fact


@fact(group=CLI)
class SecureBootKeys(BaseModel):
    keys: list[str]
