from typing import Literal

from alerting.backend.data import AlertData
from alerting.backend.generator import BaseArtefactAlertGenerator
from alerting.models import AlertSeverity
from humitifier_common.artefacts import ZFS, ZFSPool, ZFSVolume


class ZFSUsageAlertGenerator(BaseArtefactAlertGenerator):
    artefact = ZFS
    verbose_name = "ZFS Usage"

    HIGH_USAGE_THRESHOLD = 90  # percentage
    WARNING_USAGE_THRESHOLD = 80  # percentage

    def generate_alerts(self) -> AlertData | list[AlertData] | None:
        if not self.artefact_data:
            return None

        zfs: ZFS = self.artefact_data

        return self.process_items(zfs.pools, "pool") + self.process_items(
            zfs.volumes, "volume"
        )

    def process_items(
        self,
        items: list[ZFSPool] | list[ZFSVolume],
        item_type: Literal["pool", "volume"],
    ) -> list[AlertData]:
        alerts = []
        for item in items:
            percent_usage = item.used_mb / item.size_mb * 100
            percent_usage = round(percent_usage, 1)
            if percent_usage > self.HIGH_USAGE_THRESHOLD:
                alerts.append(
                    AlertData(
                        severity=AlertSeverity.CRITICAL,
                        message=f"ZFS {item_type} '{item.name}' usage ({percent_usage}%) exceeds {self.HIGH_USAGE_THRESHOLD}%",
                        custom_identifier=f"{item_type}-{item.name}",
                    )
                )
            elif percent_usage > self.WARNING_USAGE_THRESHOLD:
                alerts.append(
                    AlertData(
                        severity=AlertSeverity.WARNING,
                        message=f"ZFS {item_type} '{item.name}' usage ({percent_usage}%) exceeds {self.WARNING_USAGE_THRESHOLD}%",
                        custom_identifier=f"{item_type}-{item.name}",
                    )
                )
        return alerts
