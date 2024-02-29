import hamp._hwtypes as hw
import pytest
import re


def _test_int(int_type, kind):
    x = int_type[1]
    y = int_type[1]
    assert x is y
    assert len(x) == 1
    z = int_type[2]
    assert len(z) == 2
    w = int_type[2]
    assert z is w
    v = w(1)
    assert isinstance(v, hw._HWValue)
    assert v.value == 1
    unsized = int_type(100)
    assert int_type.unsized.expr[1] == 0
    assert unsized.value == 100


def test_uint():
    _test_int(hw.uint, "uint")


def test_sint():
    _test_int(hw.sint, "sint")


def test_resets():
    x = hw.async_reset
    assert isinstance(x, hw._HWType) and x.kind == "async_reset"
    y = hw.sync_reset
    assert isinstance(y, hw._HWType) and y.kind == "sync_reset"


def _assert_value_error(type, value):
    with pytest.raises(
        ValueError,
        match=re.escape(f"{str(type)} cannot hold the value {value:#x}"),
    ):
        type(value)


def test_uint_values():
    t1 = hw.uint[1]
    assert t1(1).value == 1
    assert t1(0).value == 0
    _assert_value_error(t1, -1)
    _assert_value_error(t1, 2)
    t2 = hw._HWType(("uint", 2))
    assert len(t2()) == 2
    for i in range(4):
        assert t2(i).value == i
    _assert_value_error(t2, -1)
    _assert_value_error(t2, -2)
    _assert_value_error(t2, 4)
    _assert_value_error(t2, 5)
    tu = hw.uint
    assert tu(0).value == 0
    assert tu(100000000).value == 100000000
    _assert_value_error(hw.uint.unsized, -1)
    assert len(t1) == 1
    assert len(hw.uint[10]) == 10


def test_sint_values():
    t1 = hw.sint[1]
    assert t1(-1).value == -1
    assert t1(0).value == 0
    _assert_value_error(t1, -2)
    _assert_value_error(t1, 1)
    t2 = hw.sint[2]
    for i in range(-2, 2):
        assert t2(i).value == i
    _assert_value_error(t2, -3)
    _assert_value_error(t2, -4)
    _assert_value_error(t2, 2)
    _assert_value_error(t2, 3)
    assert len(t1) == 1
    assert len(hw.sint[10]) == 10


def test_arrays():
    t1 = hw.uint[3]
    a1 = t1[10]
    assert repr(a1) == "uint[3][10]"
    assert a1.size == 10
    assert a1.type == hw.uint[3]
    assert len(a1) == 30


def test_clock_reset():
    t1 = hw.clock
    assert len(t1) == 1
    t2 = hw.reset
    assert len(t2) == 1
    assert str(t1) == "clock"
    assert str(t2) == "reset"
    assert t1(0).value == 0
    assert t1(1).value == 1
    _assert_value_error(t1, 2)


def test_type_caching():
    t = ("array", 3, ("uint", 2))
    t1 = hw.hwtype(t)
    t2 = hw.hwtype(t)
    assert id(t1) == id(t2)


def test_equivalent():
    assert hw.equivalent(hw.uint[2], hw.uint[2])
    assert not hw.equivalent(hw.uint[2], hw.uint[3])
    assert not hw.equivalent(hw.uint[2], hw.sint[2])
    assert hw.equivalent(hw.uint[1][10], hw.uint[1][10])
    assert not hw.equivalent(hw.sint[1][10], hw.uint[1][10])
    assert not hw.equivalent(hw.uint[1][10], hw.uint[1][11])
    assert not hw.equivalent(hw.uint[1][10], hw.uint[2][10])
    assert hw.equivalent(hw.uint[1][10][2], hw.uint[1][10][2])
    assert not hw.equivalent(hw.sint[1][10][2], hw.uint[1][10][2])
    assert not hw.equivalent(hw.uint[1][10][2], hw.uint[1][10][3])
    assert not hw.equivalent(hw.uint[1][10][2], hw.uint[1][11][2])
    assert not hw.equivalent(hw.uint[1][10][2], hw.uint[2][10][2])
    assert hw.equal(("clock", 1), hw.clock.expr)
    assert hw.equal(("reset", 1), hw.reset.expr)
    assert hw.equal(("async_reset", 1), hw.async_reset.expr)


def test_errors():
    with pytest.raises(ValueError, match=r"Malformed type"):
        hw.bitsize(2)
    with pytest.raises(TypeError, match=r"Cannot get underlaying type"):
        hw.uint[3].type
    with pytest.raises(TypeError, match=r"Cannot get size of"):
        hw.uint[3].size
