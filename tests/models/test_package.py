from humitifier.models.package import Package


example_boltdata = {
    "target": "test",
    "action": "task",
    "object": "factpoc::scan_packages",
    "status": "success",
    "value": {"packages": [{"name": "quota", "version": "4.01"}, {"name": "libini_config", "version": "1.3.1"}]},
}


def test_load_package_correctly_loads_package():
    slug, packages = Package.from_boltdata(example_boltdata)
    assert len(packages) == 2
    assert packages[0].name == "quota"
    assert packages[0].version == "4.01"
    assert packages[1].name == "libini_config"
    assert packages[1].version == "1.3.1"
    assert slug == "test"
