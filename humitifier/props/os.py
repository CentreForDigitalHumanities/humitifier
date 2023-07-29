from humitifier.html import HtmlString, KvRow
from humitifier.facts.hostnamectl import HostnameCtl

_HtmlComponent = HtmlString | KvRow


class Os(str):

    @classmethod
    @property
    def alias(cls) -> str:
        return "os"
    
    @staticmethod
    def _get_ctl(host_state) -> str:
        out = host_state[HostnameCtl.alias]
        return HostnameCtl.from_stdout(out)
    
    @classmethod
    def from_host_state(cls, host_state) -> "Os":
        return cls(cls._get_ctl(host_state).os)
    
    def component(self, html_cls: type[_HtmlComponent]) -> _HtmlComponent:
        match html_cls.__name__:
            case HtmlString.__name__:
                return HtmlString(self)
            case KvRow.__name__:
                return KvRow(
                    label="OS", 
                    value=HtmlString(self)
                )
            case _:
                raise TypeError(f"Unsupported html component type: {html_cls}")