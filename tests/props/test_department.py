import pytest
from humitifier.html import HtmlString, KvRow
from humitifier.props import Department
from humitifier.props.protocols import Property, Filterable
from humitifier.state.host import HostState


@pytest.mark.parametrize("htmlcls", [HtmlString, KvRow])
def test_department_components(htmlcls):
    department = Department("engineering")
    assert isinstance(department.component(htmlcls), htmlcls)


@pytest.mark.parametrize("protocol", [Property, Filterable])
def test_department_implements_protocol(protocol):
    assert isinstance(Department, protocol)



def test_department_from_host_state():
    state = HostState(
        fqdn=None,
        view_cfg=None,
        data={Department.alias: Department("engineering")}
    )
    department = Department.from_host_state(state)
    assert isinstance(department, Department)
    assert department == "engineering"


