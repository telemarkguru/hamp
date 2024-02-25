from hamp._show import show_type, show_expr
from pytest import raises


def test_show_type():
    assert show_type(("uint", 3)) == "uint[3]"
    assert show_type(("sint", 3)) == "sint[3]"
    assert show_type(("clock", 1)) == "clock"
    assert show_type(("reset", 1)) == "reset"
    assert show_type(("async_reset", 1)) == "async_reset"
    assert show_type(("array", 3, ("uint", 2))) == "uint[2][3]"
    assert (
        show_type(("struct", ("a", ("uint", 2), 0), ("b", ("clock", 1), 1)))
        == "{a: uint[2], b: flip clock}"
    )
    with raises(ValueError, match="Malformed type: 3"):
        show_type(3)


def test_show_expr():
    assert show_expr((0, 1)) == "0x1"
    assert show_expr((0, "abc")) == "abc"
    assert show_expr((0, (".", (("struct",), "b"), "c"))) == "b.c"
    assert show_expr((0, (".", (("instance",), "b"), "c"))) == "b.c"
    assert show_expr((0, ("[]", (("array",), "b"), (0, "c")))) == "b[c]"
    assert show_expr((0, {"a": (0, 1), "b": (0, "xyz")})) == "{a: 0x1, b: xyz}"
    assert show_expr((0, ("add", (0, 1), (0, "x")))) == "add(0x1, x)"
    assert show_expr((0, [(0, 1), (0, "abc")])) == "[0x1, abc]"
    with raises(ValueError, match=r"Malformed op argument: 3"):
        show_expr((0, ("add", (0, 1), 3)))
    with raises(ValueError, match=r"Malformed expression: 3"):
        show_expr(3)
