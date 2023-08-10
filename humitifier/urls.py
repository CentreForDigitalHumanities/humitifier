from enum import Enum


class Url(Enum):
    Index = "/"
    HostIssuesBase = "/host-issues"
    HostDetailsBase = "/host-details"
    HostDetails = "/host-details/{fqdn}"
    CloseModal = "/hx-close"