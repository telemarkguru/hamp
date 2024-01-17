from hamp._builder import _CodeBuilder, build
from hamp._module import module, input, output, wire, modules, attribute
from hamp._hwtypes import uint, sint
from hamp._struct import struct, flip
from hamp._db import validate
from textwrap import dedent
from pytest import raises
from pprint import pprint


@struct
class A:
    a: uint[2]
    b: flip(uint[2])


@struct
class B:
    c: A
    d: flip(A)
    e: sint[4]


@struct
class C:
    f: A[3]


def _module():
    modules.clear()
    mi = module("mod::inst")
    mi.w = wire(sint[2])
    mi.i = input(uint[2])
    mi.p = input(C)
    m = module("mod")
    m.x = output(uint[11])
    m.xx = output(uint[11])
    m.xs = output(sint[11])
    m.y = input(uint[10])
    m.z = wire(uint[10])
    m.s = wire(uint[10][20])
    m.s2 = wire(uint[10][20][2])
    m.b = wire(B)
    m.ba = wire(C[3])
    m.p = input(C)
    m.inst = mi()
    m.att1 = attribute(3)
    return m, mi


def _setup():
    m, _ = _module()
    b = _CodeBuilder(m)
    return b


def test_module_builder():
    m, mi = _module()
    db = {}
    build(mi, db)
    build(m, db)

    with open("m.json", "w") as fh:
        pprint(db, stream=fh)
    validate(db)


def test_code_builder():
    b = _setup()
    b.x = 3
    assert b.code == [("connect", (("uint", 11), "x"), (("uint", 11), 3))]

    b.x = b.y + b.z
    with b.if_stmt(b.y == b.z):
        b.x = 7
    with b.elif_stmt(b.y > b.z):
        b.x = 10
    with b.else_stmt():
        b.x = 0

    assert b.code == [
        # fmt: off
        ("connect", (("uint", 11), "x"), (("uint", 11), 3)),
        ("connect",
            (("uint", 11), "x"),
            (("uint", 11), ("+", (("uint", 10), "y"), (("uint", 10), "z")))
        ),
        ("when",
            (("uint", 1), ("==", (("uint", 10), "y"), (("uint", 10), "z"))), (
                ("connect", (("uint", 11), "x"), (("uint", 11), 7)),
        )),
        ("else-when",
            (("uint", 1), (">", (("uint", 10), "y"), (("uint", 10), "z"))), (
                ("connect", (("uint", 11), "x"), (("uint", 11), 10)),
        )),
        ("else", (
            ("connect", (("uint", 11), "x"), (("uint", 11), 0)),
        )),
        # fmt: on
    ]

    x = "(('uint', 11), 'x')"
    y = "(('uint', 10), 'y')"
    z = "(('uint', 10), 'z')"
    assert (
        str(b)
        == dedent(
            f"""
        ('connect', {x}, (('uint', 11), 3))
        ('connect', {x}, (('uint', 11), ('+', {y}, {z})))
        ('when', (('uint', 1), ('==', {y}, {z})), (
            ('connect', {x}, (('uint', 11), 7))
        ))
        ('else-when', (('uint', 1), ('>', {y}, {z})), (
            ('connect', {x}, (('uint', 11), 10))
        ))
        ('else', (
            ('connect', {x}, (('uint', 11), 0))
        ))
    """
        ).strip()
    )


def test_op2():
    """Test operands with 2 arguments"""

    b = _setup()
    x = (("uint", 11), "x")
    y = (("uint", 10), "y")
    z = (("uint", 10), "z")
    xs = (("sint", 11), "xs")

    def chk(op, v0=y, v1=z, rsize=None):
        if isinstance(v0, int):
            v0 = (("uint", -1), v0)
        if isinstance(v1, int):
            v1 = (("uint", -1), v1)
        rsize = rsize or 11
        assert b.code[-1] == (
            "connect",
            (("uint", 11), "x"),
            (("uint", rsize), (op, v0, v1)),
        )

    b.x = b.y + b.z
    chk("+")

    b.x = 1 + b.z
    chk("+", v0=1)

    b.x = b.y - b.z
    chk("-")

    b.x = 2 - b.z
    chk("-", v0=2)

    b.x = b.y * b.z
    chk("*", rsize=20)

    b.x = 10 * b.z
    chk("*", v0=10, rsize=14)

    b.x = 10 // b.z
    chk("//", v0=10, rsize=4)

    b.x = b.y % b.z
    chk("%", rsize=10)

    # b.x = 11 % b.z
    # chk("%", v0=11)

    b.x = b.y >> b.z
    chk(">>", rsize=10)

    b.x = 11 >> b.z
    chk(">>", v0=11, rsize=4)

    b.x = b.y >> 11
    chk(">>", v1=11, rsize=1)

    b.x = b.y << b.z
    chk("<<", rsize=1033)

    b.x = 3 << b.z
    chk("<<", v0=3, rsize=5)

    b.x = b.y << 3
    chk("<<", v1=3, rsize=13)

    b.x = b.y | b.z
    chk("|", rsize=10)

    b.x = 0x7 | b.z
    chk("|", v0=7, rsize=10)

    b.x = b.y & b.z
    chk("&", rsize=10)

    b.x = 0x7 & b.z
    chk("&", v0=7, rsize=10)

    b.x = b.y ^ b.z
    chk("^", rsize=10)

    b.x = 0x7 ^ b.z
    chk("^", v0=7, rsize=10)

    b.x = b.y == b.z
    chk("==", rsize=1)

    b.x = b.y != b.z
    chk("!=", rsize=1)

    b.x = b.y > b.z
    chk(">", rsize=1)

    b.x = b.y > 1
    chk(">", v1=1, rsize=1)

    b.x = b.y > 10
    chk(">", v1=10, rsize=1)

    b.x = b.y >= b.z
    chk(">=", rsize=1)

    b.x = b.y < b.z
    chk("<", rsize=1)

    b.x = b.y <= b.z
    chk("<=", rsize=1)

    b.x = +b.y
    assert b.code[-1] == ("connect", x, y)

    b.xs = -b.y
    assert b.code[-1] == ("connect", xs, (("sint", 11), ("neg", y)))

    b.x = ~b.y
    assert b.code[-1] == ("connect", x, (("uint", 10), ("not", y)))

    b.x = b.cat(b.y, b.z)
    chk("cat", rsize=20)

    b.b.e = b.cvt(b.x)
    bt = (
        "struct",
        ("c", ("struct", ("a", ("uint", 2), 0), ("b", ("uint", 2), 1)), 0),
        ("d", ("struct", ("a", ("uint", 2), 0), ("b", ("uint", 2), 1)), 1),
        ("e", ("sint", 4), 0),
    )
    assert b.code[-1] == (
        "connect",
        (("sint", 4), (".", (bt, "b"), "e")),
        (("sint", 12), ("cvt", x)),
    )

    b.b.e = b.cvt(b.b.e)
    assert b.code[-1] == (
        "connect",
        (("sint", 4), (".", (bt, "b"), "e")),
        (("sint", 4), ("cvt", (("sint", 4), (".", (bt, "b"), "e")))),
    )


def test_expressions():
    """Test nested expressions"""

    b = _setup()
    x = (("uint", 11), "x")
    y = (("uint", 10), "y")
    z = (("uint", 10), "z")
    s = (("array", 20, (("uint", 10))), "s")

    b.x = ((b.y + 1) // b.z + (1 + b.s[b.x + b.y])) % 32
    e1 = (("uint", 12), ("+", x, y))
    e8 = (("uint", 10), ("[]", s, e1))
    e2 = (("uint", 11), ("+", (("uint", -1), 1), e8))
    e4 = (("uint", 11), ("+", y, (("uint", -1), 1)))
    e5 = (("uint", 11), ("//", e4, z))
    e6 = (("uint", 12), ("+", e5, e2))
    e3 = (("uint", 6), ("%", e6, (("uint", -1), 32)))
    assert b.code[-1] == ("connect", x, e3)


def test_logop():
    """Test and/or/not"""

    b = _setup()
    x = (("uint", 11), "x")
    y = (("uint", 10), "y")
    z = (("uint", 10), "z")

    def orr(p):
        return (("uint", 1), ("orr", p))

    b.x = b.and_expr(b.y, b.z)
    assert b.code[-1] == ("connect", x, (("uint", 1), ("&", orr(y), orr(z))))

    b.x = b.or_expr(b.y, b.z)
    assert b.code[-1] == ("connect", x, (("uint", 1), ("|", orr(y), orr(z))))

    b.x = b.not_expr(b.y)
    assert b.code[-1] == ("connect", x, (("uint", 1), ("not", orr(y))))

    b.x = b.and_expr(b.y, 10)
    assert b.code[-1] == (
        "connect",
        x,
        (("uint", 1), ("&", orr(y), (("uint", 1), 1))),
    )


def test_bit_slicing():
    """Test var[x:y]"""

    b = _setup()
    b.xx = b.x[3:2]
    xx = (("uint", 11), "xx")
    x = (("uint", 11), "x")

    assert b.code[-1] == (
        "connect",
        xx,
        (("uint", 2), ("bits", x, (("uint", -1), 3), (("uint", -1), 2))),
    )

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
    xx = (("uint", 11), "xx")
    x = (("uint", 11), "x")
    s = (("array", 20, (("uint", 10))), "s")
    s2 = (("array", 2, s[0]), "s2")
    y = (("uint", 10), "y")

    b.xx = b.s[b.x]
    assert b.code[-1] == ("connect", xx, (("uint", 10), ("[]", s, x)))

    b.xx = b.s[1]
    assert b.code[-1] == (
        "connect",
        xx,
        (("uint", 10), ("[]", s, (("uint", -1), 1))),
    )

    b.xx = b.s2[1][2]
    assert b.code[-1] == (
        "connect",
        xx,
        (
            ("uint", 10),
            ("[]", (s[0], ("[]", s2, (("uint", -1), 1))), (("uint", -1), 2)),
        ),
    )

    b.s[b.x] = b.y
    assert b.code[-1] == ("connect", (("uint", 10), ("[]", s, x)), y)

    with raises(IndexError, match=r"s\[21\] is out of range \(size=20\)"):
        b.y = b.s[21]

    with raises(TypeError, match=r"is not subscriptable"):
        b.y = b.b[2]

    b.s[b.x] = 3

    b.s2[1] = b.s2[0]

    assert b.s2[1]._full_name() == "s2[]"
    assert b.s2[1][2]._full_name() == "s2[][]"


def test_struct_member_access():
    """Test x.a, a.b.c etc"""

    b = _setup()

    b.b.c.a = b.b.d.b
    b.b.c.a = 1

    assert b.y._full_name() == "y"
    assert b.b._full_name() == "b"
    assert b.b.c.a._full_name() == "b.c.a"
    assert b.ba[2].f[1].a._full_name() == "ba[].f[].a"

    with raises(AttributeError, match=r"has no member bix"):
        b.b.c.bix

    b.p.f[1].b = 1
    with raises(TypeError, match=r"Not allowed to assign to p.f\[\].a"):
        b.p.f[1].a = 1
    with raises(TypeError, match=r"Not allowed to assign to p.f\[\]"):
        b.p.f[1] = 1

    b.b.c.b = 1
    b.b.c.a = 1
    b.b.d.a = 1
    b.b.d.b = 1


def test_instance_port_access():
    b = _setup()

    b.inst.i = 3
    assert b.inst._full_name() == "inst"
    assert b.inst.i._full_name() == "inst.i"

    b.inst.p.f[1].a = 1
    with raises(TypeError, match=r"Not allowed to assign to inst.p.f\[\].b"):
        b.inst.p.f[1].b = 1


def test_assign_type_checking():
    b = _setup()
    with raises(TypeError, match="Cannot assign non-equivalent"):
        b.b = b.b.c
    with raises(AttributeError, match="Module mod::mod has no member nada"):
        b.nada = 1
    with raises(AttributeError, match="Module mod::mod has no member nada"):
        b.b = b.nada
    with raises(AttributeError, match="Module mod::inst has no member nada"):
        b.inst.nada = 1
    with raises(AttributeError, match="Module mod::inst has no member nada"):
        b.b = b.inst.nada
    with raises(TypeError, match="Cannot access w in instance of mod::inst"):
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
        b.inst.i = b.b.c
    with raises(
        TypeError, match="Cannot assign non-input of instance inst: w"
    ):
        b.inst.w = b.b.c
    with raises(TypeError, match="Cannot assign to instance inst"):
        b.inst = 1
    with raises(TypeError, match="Cannot assign value of unsupported type"):
        b.att1 = 3
    with raises(TypeError, match="Cannot assign to input"):
        b.y = 3
