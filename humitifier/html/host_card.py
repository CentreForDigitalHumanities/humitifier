from dataclasses import dataclass
from jinja2 import Template
from humitifier.urls import Url

from .unordered_list import UnorderedList

    
@dataclass
class HostCard:
    fqdn: str
    title: str
    properties: UnorderedList
    issue_count: int

    @property
    def modal_url(self) -> str:
        return f"{Url.HostDetailsBase.value}/{self.fqdn}"
    
    @property
    def issue_url(self) -> str:
        return f"{Url.HostIssuesBase.value}/{self.fqdn}"
    
    template = Template(
        """<article class="grid-item">
            <header><h3>{{ title }}</h3></header>
            {{ properties.render()|safe }}
            <footer>
                <button hx-swap="none" hx-get="{{ modal_url }}">Details</button>
                {% if issue_count > 0 %}
                <button hx-swap="none" hx-get="{{ issue_url }}">{{ issue_count }} Issue(s)</button>
                {% else %}
                <button disabled>No Issues!</button>
                {% endif %}
            </footer>
        </article>"""
    )

    def render(self) -> str:
        return self.template.render(
            title=self.title,
            properties=self.properties,
            issue_count=self.issue_count,
            modal_url=self.modal_url,
            issue_url=self.issue_url,
        )
    