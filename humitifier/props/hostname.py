from humitifier.models.host_state import HostState
from humitifier.facts.hostnamectl import HostnameCtl
from humitifier.html import HtmlString, KvRow

_HtmlComponent = HtmlString | KvRow


class Hostname(str):

    @classmethod
    @property
    def alias(cls) -> str:
        return "hostname"
    
    @staticmethod
    def _get_ctl(host_state: HostState) -> HostnameCtl:
        stdout = host_state[HostnameCtl.alias]
        return HostnameCtl.from_stdout(stdout)
    
    @classmethod
    def from_host_state(cls, host_state: HostState) -> "Hostname":
        ctl = cls._get_ctl(host_state)
        return cls(ctl.hostname)
    
    def component(self, html_cls: type[_HtmlComponent]) -> _HtmlComponent:
        match html_cls.__name__:
            case HtmlString.__name__:
                return HtmlString(self)
            case KvRow.__name__:
                return KvRow(
                    label="Hostname", 
                    value=HtmlString(self)
                )
            case _:
                raise TypeError(f"Unsupported html component type: {html_cls}")