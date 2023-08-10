from dataclasses import dataclass
from jinja2 import Template
from .protocols import HtmlComponent

    
@dataclass
class HxSwap:
    component: HtmlComponent
    target: str
    template = Template(
        """<div hx-swap-oob="{{target}}">{{component.render()|safe}}</div>"""
    )

    def render(self) -> str:
        return self.template.render(
            component=self.component, 
            target=self.target
        )