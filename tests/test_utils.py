from humitifier import utils


def test_flatten_list():
    assert utils.flatten_list([[1, 2], [3, 4]]) == [1, 2, 3, 4]


def test_unpack_bolt():
    data = [{"facts": {"a": "a"}}, {"packages": {"b": "b"}}]
    facts, packages = utils.unpack_bolt_data(data)
    assert facts["a"] == "a"
    assert packages["b"] == "b"
