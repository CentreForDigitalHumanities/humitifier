import pytest
from humitifier.html import HtmlString, KvRow
from humitifier.props import Department
from humitifier.props.protocols import Property, Filterable
from unittest.mock import patch


def test_department_implements_prop_protocol():
    assert isinstance(Department, Property)


def test_department_implements_filterable_protocol():
    assert isinstance(Department, Filterable)


def test_department_from_host_state():
    with patch("humitifier.props.department.HostState") as mock_host_state:
        mock_host_state.metadata = {"department": "engineering"}
        department = Department.from_host_state(mock_host_state)
        assert isinstance(department, Department)
        assert department == "engineering"


@pytest.mark.parametrize("htmlcls", [HtmlString, KvRow])
def test_department_component_has_target_componenets(htmlcls):
    department = Department("engineering")
    assert isinstance(department.component(htmlcls), htmlcls)