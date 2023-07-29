from humitifier.facts.hostnamectl import HostnameCtl
from humitifier.html import HtmlString, KvRow

_HtmlComponent = HtmlString | KvRow


class Virtualization(str):

    @classmethod
    @property
    def alias(cls) -> str:
        return "virtualization"
    
    @staticmethod
    def _get_ctl(host_state) -> str:
        out = host_state[HostnameCtl.alias]
        return HostnameCtl.from_stdout(out)
    
    @classmethod
    def from_host_state(cls, host_state) -> "Virtualization":
        ctl = cls._get_ctl(host_state)
        return cls(ctl.virtualization)
    
    def component(self, html_cls: type[_HtmlComponent]) -> _HtmlComponent:
        match html_cls.__name__:
            case HtmlString.__name__:
                return HtmlString(self)
            case KvRow.__name__:
                return KvRow(
                    label="Virtualization", 
                    value=HtmlString(self)
                )
            case _:
                raise TypeError(f"Unsupported html component type: {html_cls}")