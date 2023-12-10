from hamp._stdlib import cat
from hamp._hwtypes import uint


def test_cat():
    assert cat(1, 2) == ("cat", 1, 2)
    assert cat(0, 1, 2) == ("cat", 0, ("cat", 1, 2))
    assert cat(0, 1, 2, 3) == ("cat", 0, ("cat", 1, ("cat", 2, 3)))
    a = uint[2](3)
    b = uint[3](1)
    c = uint[1](0)
    assert cat(a, b, c) == ("cat", a, ("cat", b, c))
