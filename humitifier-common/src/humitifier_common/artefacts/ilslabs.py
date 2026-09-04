"""
A collection of facts that are ILS Labs specific
"""

from pydantic import BaseModel, ConfigDict

from humitifier_common.artefacts.groups import ILSLABS
from humitifier_common.artefacts.registry import fact
from humitifier_common.artefacts.registry.registry import ArtefactMetadata

##
## PyInfra
##


class PyInfraReportSummary(BaseModel):
    total_operations: int
    successful_operations: int
    failed_operations: int
    changed_operations: int


class PyInfraReportOperation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    names: list[str]
    op_hash: str
    start_time: str
    end_time: str
    duration_seconds: float
    success: bool
    changed: bool | None
    error: bool
    retries: int
    commands_count: int


class PyInfraReportHostInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    hostname: str
    role: str
    layers: list[str]
    otap_stage: str


@fact(group=ILSLABS, metadata=ArtefactMetadata(null_is_valid=True))
class PyInfraReport(BaseModel):
    model_config = ConfigDict(extra="ignore")

    success: bool
    host: str
    start_time: str
    end_time: str
    host_info: PyInfraReportHostInfo
    duration_seconds: float
    components: list[str]
    summary: PyInfraReportSummary
    failed_operations: list[PyInfraReportOperation] = []
