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
    mi = module("inst")
    mi.w = wire(sint[2])
    mi.i = input(uint[2])
    m = module("mod")
    m.x = output(uint[11])
    m.xs = output(sint[11])
    m.y = input(uint[10])
    m.z = wire(uint[10])
    m.s = wire(uint[10][20])
    m.s2 = wire(uint[10][20][2])
    m.b = wire(B)
    m.inst = mi()
    b = _CodeBuilder(m)
    return b


def test_code_builder():
    b = _setup()
    b.x = 3
    assert b.code == [("connect", "x", ("uint", 11, 3))]

    b.x = b.y + b.z
    with b.if_stmt(b.y == b.z):
        b.x = 7
    with b.elif_stmt(b.y > b.z):
        b.x = 10
    with b.else_stmt():
        b.x = 0

    assert b.code == [
        ("connect", "x", ("uint", 11, 3)),
        ("connect", "x", ("+", "y", "z")),
        ("when", ("==", "y", "z")),
        ("connect", "x", ("uint", 11, 7)),
        ("else_when", (">", "y", "z")),
        ("connect", "x", ("uint", 11, 10)),
        ("else",),
        ("connect", "x", ("uint", 11, 0)),
        ("end_when",),
    ]

    assert (
        str(b)
        == dedent(
            """
        ('connect', 'x', ('uint', 11, 3))
        ('connect', 'x', ('+', 'y', 'z'))
        ('when', ('==', 'y', 'z'))
            ('connect', 'x', ('uint', 11, 7))
        ('else_when', ('>', 'y', 'z'))
            ('connect', 'x', ('uint', 11, 10))
        ('else',)
            ('connect', 'x', ('uint', 11, 0))
        ('end_when',)
    """
        ).strip()
    )


def test_op2():
    """Test operands with 2 arguments"""

    b = _setup()

    def chk(op, v0="y", v1="z"):
        if isinstance(v0, int):
            v0 = ("uint", -1, v0)
        if isinstance(v1, int):
            v1 = ("uint", -1, v1)
        assert b.code[-1] == ("connect", "x", (op, v0, v1))

    b.x = b.y + b.z
    chk("+")

    b.x = 1 + b.z
    chk("+", v0=1)

    b.x = b.y - b.z
    chk("-")

    b.x = 2 - b.z
    chk("-", v0=2)

    b.x = b.y * b.z
    chk("*")

    b.x = 10 * b.z
    chk("*", v0=10)

    b.x = 10 // b.z
    chk("//", v0=10)

    b.x = b.y % b.z
    chk("%")

    # b.x = 11 % b.z
    # chk("%", v0=11)

    b.x = b.y >> b.z
    chk(">>")

    b.x = 11 >> b.z
    chk(">>", v0=11)

    b.x = b.y >> 11
    chk(">>", v1=11)

    b.x = b.y << b.z
    chk("<<")

    b.x = 3 << b.z
    chk("<<", v0=3)

    b.x = b.y << 3
    chk("<<", v1=3)

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

    b.x = b.y > 10
    chk(">", v1=10)

    b.x = b.y >= b.z
    chk(">=")

    b.x = b.y < b.z
    chk("<")

    b.x = b.y <= b.z
    chk("<=")

    b.x = +b.y
    assert b.code[-1] == ("connect", "x", "y")

    b.xs = -b.y
    assert b.code[-1] == ("connect", "xs", ("neg", "y"))

    b.x = ~b.y
    assert b.code[-1] == ("connect", "x", ("not", "y"))

    b.x = b.cat(b.y, b.z)
    chk("cat")

    b.b.e = b.cvt(b.x)
    assert b.code[-1] == ("connect", (".", "b", "e"), ("cvt", "x"))

    b.b.e = b.cvt(b.b.e)
    assert b.code[-1] == ("connect", (".", "b", "e"), ("cvt", (".", "b", "e")))


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
                ("//", ("+", "y", ("uint", -1, 1)), "z"),
                ("+", ("uint", -1, 1), ("[]", "s", ("+", "x", "y"))),
            ),
            ("uint", -1, 32),
        ),
    )


def test_logop():
    """Test and/or/not"""

    b = _setup()

    b.x = b.and_expr(b.y, b.z)
    assert b.code[-1] == (
        "connect",
        "x",
        ("&", ("orr", "y"), ("orr", "z")),
    )

    b.x = b.or_expr(b.y, b.z)
    assert b.code[-1] == (
        "connect",
        "x",
        ("|", ("orr", "y"), ("orr", "z")),
    )

    b.x = b.not_expr(b.y)
    assert b.code[-1] == ("connect", "x", ("not", ("orr", "y")))

    b.x = b.and_expr(b.y, 10)
    assert b.code[-1] == ("connect", "x", ("&", ("orr", "y"), ("uint", 1, 1)))


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

    with raises(TypeError, match=r"Expected constant bit-slice"):
        b.y = b.x[None]


def test_array_indexing():
    """Test x[y] = z, x = y[z], etc"""

    b = _setup()

    b.y = b.s[b.x]
    assert b.code[-1] == ("connect", "y", ("[]", "s", "x"))

    b.y = b.s[1]
    assert b.code[-1] == ("connect", "y", ("[]", "s", ("uint", -1, 1)))

    b.s[b.x] = b.y
    assert b.code[-1] == ("connect", ("[]", "s", "x"), "y")

    with raises(IndexError, match=r"s\[21\] is out of range \(size=20\)"):
        b.y = b.s[21]

    with raises(TypeError, match=r"is not subscriptable"):
        b.y = b.b[2]

    b.s[b.x] = 3

    b.s2[1] = b.s2[0]


def test_struct_member_access():
    """Test x.a, a.b.c etc"""

    b = _setup()

    b.b.c.a = b.b.d.b
    b.b.c.a = 1

    with raises(AttributeError, match=r"has no member bix"):
        b.b.c.bix


def test_instance_port_access():
    b = _setup()

    b.inst.i = 3


def test_assign_type_checking():
    b = _setup()
    with raises(TypeError, match="Cannot assign non-equivalent"):
        b.b = b.b.c
    with raises(AttributeError, match="Module mod has no member nada"):
        b.nada = 1
    with raises(AttributeError, match="Module mod has no member nada"):
        b.b = b.nada
    with raises(AttributeError, match="Module inst has no member nada"):
        b.inst.nada = 1
    with raises(AttributeError, match="Module inst has no member nada"):
        b.b = b.inst.nada
    with raises(TypeError, match="Cannot access w in instance of inst"):
        b.b = b.inst.w
    with raises(TypeError, match="Cannot infer integer for type"):
        b.b = 3
    with raises(TypeError, match="Both operands must have same sign"):
        b.b.e + b.b.d.b
    with raises(TypeError, match="Shift amount must be an unsigned value"):
        b.b.d.b << b.b.e
    with raises(TypeError, match="Shift amount must be an unsigned value"):
        b.b.d.b >> b.b.e
    with raises(TypeError, match="Cannot assign non-equivalent type"):
        b.b.c = b.y
    with raises(TypeError, match="Cannot assign non-equivalent type"):
        b.s[3] = b.b.c
    with raises(TypeError, match="Cannot assign non-equivalent type"):
        b.inst.w = b.b.c
