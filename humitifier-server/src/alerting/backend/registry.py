from typing import TYPE_CHECKING

from alerting.backend.data import AlertGeneratorType

from humitifier_common.artefacts.registry.registry import ArtefactType
from humitifier_common.scan_data import ScanOutput


if TYPE_CHECKING:
    from .generator import BaseScanAlertGenerator, BaseArtefactAlertGenerator


class _AlertGeneratorRegistry:

    def __init__(self):
        self._scan_alert_generators: list[type["BaseScanAlertGenerator"]] = []
        self._artefact_alert_generators: list[type["BaseArtefactAlertGenerator"]] = []

    def register(
        self,
        generator: type["BaseScanAlertGenerator"] | type["BaseArtefactAlertGenerator"],
    ):
        match generator._type:
            case AlertGeneratorType.ARTEFACT:
                self._artefact_alert_generators.append(generator)
            case AlertGeneratorType.SCAN:
                self._scan_alert_generators.append(generator)

    def get(
        self, name: str
    ) -> type["BaseScanAlertGenerator"] | type["BaseArtefactAlertGenerator"] | None:
        for alert_generator in self._artefact_alert_generators:
            if alert_generator._creator == name:
                return alert_generator

        for alert_generator in self._scan_alert_generators:
            if alert_generator._creator == name:
                return alert_generator

        return None

    def get_scan_alert_generators(
        self, scan_output: ScanOutput
    ) -> list["BaseScanAlertGenerator"]:
        return [cls(scan_output) for cls in self._scan_alert_generators]

    def get_artefact_alert_generators(
        self, scan_output: ScanOutput
    ) -> list["BaseArtefactAlertGenerator"]:
        generators = []

        artefacts = list(scan_output.facts.keys())
        artefacts += list(scan_output.metrics.keys())

        for generator in self._artefact_alert_generators:
            artefact_name = generator.artefact.__artefact_name__
            if artefact_name in artefacts:
                data = scan_output.get_artefact_data(artefact_name)
                generators.append(generator(data, scan_output.scan_date))

        return generators

    def get_alert_types(self) -> list[str]:
        output = [
            generator.verbose_name for generator in self._artefact_alert_generators
        ]
        output += [generator.verbose_name for generator in self._scan_alert_generators]

        return sorted(set(output))


alert_generator_registry = _AlertGeneratorRegistry()
