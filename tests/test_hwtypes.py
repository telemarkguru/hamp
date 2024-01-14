import hamp._hwtypes as hw
import pytest
import re


def _test_int(int_type):
    x = int_type[1]
    y = int_type[1]
    assert x is y
    assert x.size == 1
    z = int_type[2]
    assert z.size == 2
    w = int_type[2]
    assert z is w
    v = w(1)
    assert isinstance(v, hw._IntValue)
    assert v.value == 1
    unsized = int_type(100)
    assert unsized.type.size == -1
    assert unsized.value == 100


def test_uint():
    _test_int(hw.uint)


def test_sint():
    _test_int(hw.sint)


def test_resets():
    x = hw.async_reset()
    assert isinstance(x, hw._AsyncReset)
    y = hw.sync_reset()
    assert isinstance(y, hw._SyncReset)


def _assert_value_error(type, value):
    with pytest.raises(
        ValueError,
        match=re.escape(f"{type.kind}[{type.size}] cannot hold value {value}"),
    ):
        type(value)


def test_uint_values():
    t1 = hw.uint[1]
    assert t1(1).value == 1
    assert t1(0).value == 0
    _assert_value_error(t1, -1)
    _assert_value_error(t1, 2)
    t2 = hw.uint[2]
    for i in range(4):
        assert t2(i).value == i
    _assert_value_error(t2, -1)
    _assert_value_error(t2, -2)
    _assert_value_error(t2, 4)
    _assert_value_error(t2, 5)
    tu = hw.uint
    assert tu(0).value == 0
    assert tu(100000000).value == 100000000
    _assert_value_error(hw._UInt(-1), -1)


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


def test_arrays():
    t1 = hw.uint[3]
    a1 = t1[10]
    assert repr(a1) == "uint[3][10]"
    assert a1.size == 10
    assert a1.type == hw.uint[3]


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
