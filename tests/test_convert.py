from hamp._convert import convert
from hamp._module import module, input, wire, modules
from hamp._hwtypes import clock, reset, uint
from textwrap import dedent


def test_closure():
    modules.clear()
    m = module("closure")

    a = 3

    def xyz(p):  # pragma: no cover
        return p + a

    def fx(x):  # pragma: no cover
        z = xyz(x + 3) + xyz(4)
        return z

    f, txt = convert(fx, m)

    assert f(1) == 14
    assert (
        txt
        == dedent(
            """
            def fx(x):
                z = xyz(x + 3) + xyz(4)
                return z
            """
        ).strip()
    )


def test_if():
    modules.clear()
    m = module("test")
    m.a = input(clock())
    m.b = wire(uint[2])
    p = 2

    def foo(x):  # pragma: no cover
        if p + 1:
            if x.a > x.b:
                z.a.b = 3  # noqa: F821
            elif x.a < x.b:
                z = 4  # noqa: F841
            else:
                z = 5  # noqa: F841

    f, txt = convert(foo, m)
    assert (
        txt
        == dedent(
            """
    def foo(x):
        if p + 1:
            with x.if_stmt(x.a > x.b):
                z.a.b = 3
            with x.elif_stmt(x.a < x.b):
                z = 4
            with x.else_stmt():
                z = 5
    """
        ).strip()
    )


def test_and_or_not():
    modules.clear()
    m = module("test")
    m.a = input(clock)
    m.b = input(uint[2])
    m.c = input(reset)

    def foo(x):  # pragma: no cover
        if x.a and b:  # noqa: F821
            z = 1
        if a or x.b:  # noqa: F821
            z += 2
        if not x.c:
            z += ~3

    f, txt = convert(foo, m)
    assert (
        txt
        == dedent(
            """
    def foo(x):
        with x.if_stmt(x.and_expr(x.a, b)):
            z = 1
        with x.if_stmt(x.or_expr(a, x.b)):
            z += 2
        with x.if_stmt(x.not_expr(x.c)):
            z += ~3
    """
        ).strip()
    )
