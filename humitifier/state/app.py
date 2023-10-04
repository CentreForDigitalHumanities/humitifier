from dataclasses import dataclass

from humitifier.config.app import AppConfig
from humitifier.props import Department
from .filterset import HostStateFilterset
from .host_collection import HostCollectionState


@dataclass
class AppState:
    filterset: HostStateFilterset
    host_collection: HostCollectionState
    config: AppConfig

    @property
    def filter_kv(self):
        return {Department.alias: Department}

    @classmethod
    def initialize(cls, config: AppConfig):
        collection_state = HostCollectionState.initialize(config)
        # collection_state = config.get_host_state_collection(config.collect_outputs())
        filterset_state = HostStateFilterset.initialize(collection_state.values(), config.filters)
        return cls(filterset=filterset_state, host_collection=collection_state, config=config)
