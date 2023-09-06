from hamp._builder import _VarBuilder, _CodeBuilder
from hamp._module import module, input, output, wire, modules
from hamp._hwtypes import uint, sint
from textwrap import dedent


def _setup():
    modules.clear()
    m = module("mod")
    m.x = wire(uint[10])
    m.y = wire(uint[10])
    m.z = wire(uint[10])
    b = _CodeBuilder(m)
    return b


def test_code_builder():
    b = _setup()
    b.x = 3
    assert b.code == [("connect", "x", 3)]

    b.x = b.y + b.z
    with b.if_stmt(b.y == b.z):
        b.x = -1
    with b.elif_stmt(b.y > b.z):
        b.x = 10
    with b.else_stmt():
        b.x = 0

    assert b.code == [
        ("connect", "x", 3),
        ("connect", "x", ("+", "y", "z")),
        ("when", ("==", "y", "z")),
        ("connect", "x", -1),
        ("else_when", (">", "y", "z")),
        ("connect", "x", 10),
        ("else",),
        ("connect", "x", 0),
        ("end_when",),
    ]

    assert (
        str(b)
        == dedent(
            """
        ('connect', 'x', 3)
        ('connect', 'x', ('+', 'y', 'z'))
        ('when', ('==', 'y', 'z'))
            ('connect', 'x', -1)
        ('else_when', ('>', 'y', 'z'))
            ('connect', 'x', 10)
        ('else',)
            ('connect', 'x', 0)
        ('end_when',)
    """
        ).strip()
    )


def test_op2():
    """Test operands with 2 arguments"""

    b = _setup()

    def chk(op, v0="y", v1="z"):
        assert b.code[-1] == ("connect", "x", (op, v0, v1))

    b.x = b.y + b.z
    chk("+")

    b.x = 1 + b.z
    chk("+", v0="uint(1)")

    b.x = b.y - b.z
    chk("-")

    b.x = -1 - b.z
    chk("-", v0="sint(-1)")

    b.x = b.y * b.z
    chk("*")

    b.x = 10 * b.z
    chk("*", v0="uint(10)")

    b.x = b.y % b.z
    chk("%")

    b.x = 11 % b.z
    chk("%", v0="uint(11)")

    b.x = b.y >> b.z
    chk(">>")

    b.x = 11 >> b.z
    chk(">>", v0="uint(11)")

    b.x = b.y << b.z
    chk("<<")

    b.x = 3 << b.z
    chk("<<", v0="uint(3)")

    b.x = b.y | b.z
    chk("|")

    b.x = 0x7 | b.z
    chk("|", v0="uint(7)")

    b.x = b.y & b.z
    chk("&")

    b.x = 0x7 & b.z
    chk("&", v0="uint(7)")

    b.x = b.y ^ b.z
    chk("^")

    b.x = 0x7 ^ b.z
    chk("^", v0="uint(7)")

    b.x = b.y == b.z
    chk("==")

    b.x = b.y != b.z
    chk("!=")

    b.x = b.y > b.z
    chk(">")

    b.x = b.y > 1
    chk(">", v1="uint(1)")

    b.x = b.y > -10
    chk(">", v1="sint(-10)")

    b.x = b.y >= b.z
    chk(">=")

    b.x = b.y < b.z
    chk("<")

    b.x = b.y <= b.z
    chk("<=")

    b.x = +b.y
    assert b.code[-1] == ("connect", "x", ("pos", "y"))

    b.x = -b.y
    assert b.code[-1] == ("connect", "x", ("neg", "y"))


def test_logop():
    """Test and/or/not"""

    b = _setup()

    b.x = b.and_expr(b.y, b.z)
    assert b.code[-1] == ("connect", "x", ("and", "y", "z"))

    b.x = b.or_expr(b.y, b.z)
    assert b.code[-1] == ("connect", "x", ("or", "y", "z"))

    b.x = b.not_expr(b.y)
    assert b.code[-1] == ("connect", "x", ("not", "y"))
