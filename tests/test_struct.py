from hamp._struct import struct, flip, hasmember, members, member, flipped
from hamp._hwtypes import uint, sint, equivalent
import pytest


def test_basic_struct():
    @struct
    class Foo:
        a: uint[1]
        b: sint[2]

    a = Foo()
    assert a["a"] == 0
    assert a.b == 0
    assert Foo.a == uint[1]
    assert Foo.b == sint[2]
    assert member(Foo, "a") == uint[1]
    with pytest.raises(AttributeError, match=r"Struct has no member x"):
        member(Foo, "x")


def test_hier_struct():
    @struct
    class Foo:
        a: sint[1]
        b: uint[3]

    @struct
    class Bar:
        a: Foo
        b: Foo

    foo_str = "{a: sint[1], b: uint[3]}"
    assert str(Foo) == foo_str
    assert str(Bar) == f"{{a: {foo_str}, b: {foo_str}}}"

    x = Bar({"a": {"a": -1, "b": 2}})

    assert hasmember(Bar, "a")
    assert hasmember(Bar, "b")
    assert hasmember(Foo, "a")
    assert hasmember(Foo, "b")
    assert not hasmember(Foo, "x")

    assert x["a"]["a"] == -1
    assert x["a"]["b"] == 2
    assert x["b"]["a"] == 0
    assert x["b"]["b"] == 0
    x["b"]["a"] = 7
    assert x["b"]["a"] == 7

    assert list(members(Foo)) == [("a", sint[1]), ("b", uint[3])]
    assert len(Foo) == 4
    assert len(Bar) == 8


def test_flip():
    @struct
    class Foo:
        a: sint[1]
        b: flip(uint[3])

    assert Foo.expr == ("struct", ("a", ("sint", 1), 0), ("b", ("uint", 3), 1))
    x = Foo(b=3)
    assert x["b"] == 3
    assert flipped(Foo, "b")
    assert not flipped(Foo, "a")


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
    assert x["b"][1] == 0
    x["b"][0] = 1
    x["b"][1] = 2
    x["b"][2] = 3
    assert x["b"][0] == 1
    assert x["b"][1] == 2
    assert x["b"][2] == 3


def test_equivalent():
    @struct
    class Z:
        a: uint[10]
        b: uint[2][3][4]

    @struct
    class Z2:
        a: uint[10]
        b: uint[2][1][4]

    @struct
    class A:
        a: sint[2]
        b: sint[4]
        x: sint[7][7]
        z: Z

    @struct
    class B:
        a: sint[2]
        b: sint[4]
        x: sint[7][7]
        z: Z

    assert equivalent(A, B)

    @struct
    class A:
        a: sint[2]
        b: sint[4]

    @struct
    class B:
        a: sint[2]
        b: sint[4]
        c: uint[1]

    assert not equivalent(A, B)

    @struct
    class A:
        a: sint[2]
        b: uint[4]

    @struct
    class B:
        a: sint[2]
        b: sint[4]

    assert not equivalent(A, B)

    @struct
    class A:
        a: sint[2]
        b: sint[4]
        x: sint[7][7]
        z: Z

    @struct
    class B:
        a: sint[2]
        b: sint[4]
        x: sint[7][7]
        z: Z2

    assert not equivalent(A, B)

    @struct
    class A:
        a: sint[2]
        b: sint[4]
        i: sint[7][7]
        z: Z

    @struct
    class B:
        a: sint[2]
        b: sint[4]
        x: sint[7][7]
        z: Z2

    assert not equivalent(A, B)

    with pytest.raises(TypeError):
        equivalent(1, 2)
