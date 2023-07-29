import pytest
from humitifier.html import InlineList, KvRow, HtmlString
from humitifier.facts.package_list import Package
from humitifier.props import PackageList
from humitifier.props.protocols import Property
from unittest.mock import patch


def test_package_list_implements_prop_protocol():
    assert isinstance(PackageList, Property)


@pytest.mark.parametrize("htmlcls", [InlineList, KvRow, HtmlString])
def test_package_list_component_has_target_componenets(htmlcls):
    package_list = PackageList([Package("vim", "8.0.0")])
    assert isinstance(package_list.component(htmlcls), htmlcls)
