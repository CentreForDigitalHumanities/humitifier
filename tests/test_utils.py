from humitifier import utils


def test_flatten_list():
    assert utils.flatten_list([[1, 2], [3, 4]]) == [1, 2, 3, 4]
