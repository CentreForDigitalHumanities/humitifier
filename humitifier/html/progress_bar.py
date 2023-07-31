from dataclasses import dataclass
from jinja2 import Template

@dataclass
class ProgressBar:
    label: str
    percentage: int
    template = Template("""
        <div class="progress" data-label="{{label}}">
            <span class="value" style="width:{{percentage}}%;"></span>
        </div>"""
    )

    def render(self) -> str:
        return self.template.render(
            label=self.label, 
            percentage=self.percentage
        )