from hamp._builder import _CodeBuilder
from hamp._module import module, input, output, wire, modules
from hamp._hwtypes import uint, sint
from hamp._struct import struct
from textwrap import dedent
from pytest import raises


@struct
class A:
    a: uint[2]
    b: uint[2]


@struct
class B:
    c: A
    d: A
    e: sint[4]


def _setup():
    modules.clear()
    m = module("mod")
    m.x = output(uint[10])
    m.y = input(uint[10])
    m.z = wire(uint[10])
    m.s = wire(uint[10][20])
    m.b = wire(B)
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
    chk("+", v0=1)

    b.x = b.y - b.z
    chk("-")

    b.x = -1 - b.z
    chk("-", v0=-1)

    b.x = b.y * b.z
    chk("*")

    b.x = 10 * b.z
    chk("*", v0=10)

    b.x = b.y % b.z
    chk("%")

    # b.x = 11 % b.z
    # chk("%", v0=11)

    b.x = b.y >> b.z
    chk(">>")

    b.x = 11 >> b.z
    chk(">>", v0=11)

    b.x = b.y << b.z
    chk("<<")

    b.x = 3 << b.z
    chk("<<", v0=3)

    b.x = b.y | b.z
    chk("|")

    b.x = 0x7 | b.z
    chk("|", v0=7)

    b.x = b.y & b.z
    chk("&")

    b.x = 0x7 & b.z
    chk("&", v0=7)

    b.x = b.y ^ b.z
    chk("^")

    b.x = 0x7 ^ b.z
    chk("^", v0=7)

    b.x = b.y == b.z
    chk("==")

    b.x = b.y != b.z
    chk("!=")

    b.x = b.y > b.z
    chk(">")

    b.x = b.y > 1
    chk(">", v1=1)

    b.x = b.y > -10
    chk(">", v1=-10)

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

    b.x = b.cat(b.y, b.z)
    chk("cat")


def test_expressions():
    """Test nested expressions"""

    b = _setup()

    b.x = ((b.y + 1) // b.z + (1 + b.s[b.x + b.y])) % 32
    assert b.code[-1] == (
        "connect",
        "x",
        (
            "%",
            (
                "+",
                ("//", ("+", "y", 1), "z"),
                ("+", 1, ("[]", "s", ("+", "x", "y"))),
            ),
            32,
        ),
    )


def test_logop():
    """Test and/or/not"""

    b = _setup()

    b.x = b.and_expr(b.y, b.z)
    assert b.code[-1] == (
        "connect",
        "x",
        ("and", ("orr", "y"), ("orr", "z")),
    )

    b.x = b.or_expr(b.y, b.z)
    assert b.code[-1] == (
        "connect",
        "x",
        ("or", ("orr", "y"), ("orr", "z")),
    )

    b.x = b.not_expr(b.y)
    assert b.code[-1] == ("connect", "x", ("not", ("orr", "y")))


def test_bit_slicing():
    """Test var[x:y]"""

    b = _setup()
    b.y = b.x[3:2]
    assert b.code[-1] == ("connect", "y", ("bits", "x", 3, 2))

    with raises(TypeError, match="s is not a bit-vector"):
        b.y = b.s[3:2]

    with raises(IndexError, match="Slice indexes must be integer constants"):
        b.y = b.x[b.z : 2]

    with raises(IndexError, match="Slice indexes must be integer constants"):
        b.y = b.x[2 : b.z]

    with raises(IndexError, match="Step in slice index not allowed"):
        b.y = b.x[2:1:3]

    with raises(IndexError, match="Slice MSB must be equal to or larger"):
        b.y = b.x[1:3]


def test_array_indexing():
    """Test x[y] = z, x = y[z], etc"""

    b = _setup()

    b.y = b.s[b.x]
    assert b.code[-1] == ("connect", "y", ("[]", "s", "x"))

    b.y = b.s[1]
    assert b.code[-1] == ("connect", "y", ("[]", "s", 1))

    b.s[b.x] = b.y
    assert b.code[-1] == ("connect", ("[]", "s", "x"), "y")

    with raises(IndexError, match=r"s\[21\] is out of range \(size=20\)"):
        b.y = b.s[21]

    with raises(TypeError, match=r"b is not an array"):
        b.y = b.b[2]


def test_struct_member_access():
    """Test x.a, a.b.c etc"""

    b = _setup()

    b.b.c.a = b.b.d.b

    with raises(AttributeError, match=r"has no member bix"):
        b.b.c.bix
