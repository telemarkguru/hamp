from hamp._struct import struct, flip, hasmember
from hamp._hwtypes import uint, sint
import pytest


def test_basic_struct():
    @struct
    class Foo:
        a: uint[1]
        b: sint[2]

    a = Foo()
    assert a.a.value == 0
    assert a.b.value == 0


def test_hier_struct():
    @struct
    class Foo:
        a: sint[1]
        b: uint[3]

    @struct
    class Bar:
        a: Foo
        b: Foo

    x = Bar()

    assert hasmember(Bar, "a")
    assert hasmember(Bar, "b")
    assert hasmember(Foo, "a")
    assert hasmember(Foo, "b")

    assert x.a.a.value == 0
    assert x.a.b.value == 0
    assert x.b.a.value == 0
    assert x.b.b.value == 0
    x.b.a = uint[3](7)
    assert x.b.a.value == 7


def test_flip():
    @struct
    class Foo:
        a: sint[1]
        b: flip(uint[3])

    assert Foo.__flips__ == set(("b",))
    x = Foo()
    assert x.b.value == 0


def test_type_error():
    with pytest.raises(TypeError, match=r"Type <[^>]+> not allowed"):

        @struct
        class Foo:
            a: sint[1]
            b: int
            c: uint[7]


def test_array_in_struct():
    @struct
    class Foo:
        a: sint[1]
        b: uint[2][3]

    x = Foo()
    assert x.b[1].value == 0
    x.b[0] = 1
    x.b[1] = 2
    x.b[2] = 3
    assert x.b[0].value == 1
    assert x.b[1].value == 2
    assert x.b[2].value == 3


