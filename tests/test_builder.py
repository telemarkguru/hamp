from hamp._module import (
    module,
    input,
    output,
    wire,
    attribute,
    register,
)
from hamp._hwtypes import uint, sint, clock, reset, u1
from hamp._struct import struct, flip
from hamp._db import validate, create
from hamp._stdlib import cvt, cat
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
    e: sint[12]


@struct
class C:
    f: A[3]


def _module():
    db = create()
    mi = module("mod::inst", db=db)
    mi.w = wire(sint[2])
    mi.i = input(uint[2], z=2)
    mi.p = input(C)
    m = module("mod", db=db)
    m.x = output(uint[20], z=1)
    m.bigx = output(uint[1033])
    m.xx = output(uint[11])
    m.xs = output(sint[11])
    m.y = input(uint[10])
    m.z = wire(uint[10])
    m.s = wire(uint[10][20], a=1)
    m.s2 = wire(uint[10][20][2])
    m.b = wire(B)
    m.ba = wire(C[3])
    m.p = input(C)
    m.clk = input(clock)
    m.rst = input(reset)
    m.r = register(B)
    m.en = wire(u1)
    m.pred = wire(u1)
    m.inst = mi(k=3)
    m.att1 = attribute(3)
    return m, mi


def _setup():
    m, _ = _module()
    b = m.bld
    return b


def test_module_builder():
    m, mi = _module()

    with open("m.json", "w") as fh:
        pprint(m.db, stream=fh)
    validate(m.db)


def test_code_builder():
    b = _setup()
    b.x = 3
    assert b._code == [("connect", (("uint", 20), "x"), (("uint", 20), 3))]

    b.x = b.y + b.z
    with b.if_stmt(b.y == b.z):
        b["x"] = 7
    with b.elif_stmt(b.y > b["z"]):
        b.x = 10
    with b.else_stmt():
        b.x = 0

    assert b._code == [
        # fmt: off
        ("connect", (("uint", 20), "x"), (("uint", 20), 3)),
        ("connect",
            (("uint", 20), "x"),
            (("uint", 11), ("+", (("uint", 10), "y"), (("uint", 10), "z")))
        ),
        ("when",
            (("uint", 1), ("==", (("uint", 10), "y"), (("uint", 10), "z"))), (
                ("connect", (("uint", 20), "x"), (("uint", 20), 7)),
        )),
        ("else-when",
            (("uint", 1), (">", (("uint", 10), "y"), (("uint", 10), "z"))), (
                ("connect", (("uint", 20), "x"), (("uint", 20), 10)),
        )),
        ("else", (
            ("connect", (("uint", 20), "x"), (("uint", 20), 0)),
        )),
        # fmt: on
    ]

    x = "(('uint', 20), 'x')"
    y = "(('uint', 10), 'y')"
    z = "(('uint', 10), 'z')"
    assert (
        str(b)
        == dedent(
            f"""
        ('connect', {x}, (('uint', 20), 3))
        ('connect', {x}, (('uint', 11), ('+', {y}, {z})))
        ('when', (('uint', 1), ('==', {y}, {z})), (
            ('connect', {x}, (('uint', 20), 7))
        ))
        ('else-when', (('uint', 1), ('>', {y}, {z})), (
            ('connect', {x}, (('uint', 20), 10))
        ))
        ('else', (
            ('connect', {x}, (('uint', 20), 0))
        ))
    """
        ).strip()
    )


def test_op2():
    """Test operands with 2 arguments"""

    b = _setup()
    x = (("uint", 20), "x")
    bigx = (("uint", 1033), "bigx")
    y = (("uint", 10), "y")
    z = (("uint", 10), "z")
    xs = (("sint", 11), "xs")

    def chk(op, v0=y, v1=z, rsize=None, x=x):
        if isinstance(v0, int):
            v0 = (("uint", v0.bit_length()), v0)
        if isinstance(v1, int):
            v1 = (("uint", v1.bit_length()), v1)
        rsize = rsize or 11
        assert b._code[-1] == (
            "connect",
            x,
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

    b.bigx = b.y << b.z
    chk("<<", rsize=1033, x=bigx)

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
    assert b._code[-1] == ("connect", x, y)

    b.xs = -b.y
    assert b._code[-1] == ("connect", xs, (("sint", 11), ("neg", y)))

    b.x = ~b.y
    assert b._code[-1] == ("connect", x, (("uint", 10), ("not", y)))

    b.x = cat(b.y, b.z)
    chk("cat", rsize=20)

    b.b.e = cvt(b.x)
    bt = (
        "struct",
        ("c", ("struct", ("a", ("uint", 2), 0), ("b", ("uint", 2), 1)), 0),
        ("d", ("struct", ("a", ("uint", 2), 0), ("b", ("uint", 2), 1)), 1),
        ("e", ("sint", 12), 0),
    )
    assert b._code[-1] == (
        "connect",
        (("sint", 12), (".", (bt, "b"), "e")),
        (("sint", 21), ("cvt", x)),
    )

    b.b.e = cvt(b.b.e)
    assert b._code[-1] == (
        "connect",
        (("sint", 12), (".", (bt, "b"), "e")),
        (("sint", 12), ("cvt", (("sint", 12), (".", (bt, "b"), "e")))),
    )


def test_expressions():
    """Test nested expressions"""

    b = _setup()
    x = (("uint", 20), "x")
    y = (("uint", 10), "y")
    z = (("uint", 10), "z")
    s = (("array", 20, (("uint", 10))), "s")

    v = b.s[b.x + b.y]
    b.x = ((b.y + 1) // b.z + (1 + v)) % 32
    e1 = (("uint", 21), ("+", x, y))
    e8 = (("uint", 10), ("[]", s, e1))
    e2 = (("uint", 11), ("+", (("uint", 1), 1), e8))
    e4 = (("uint", 11), ("+", y, (("uint", 1), 1)))
    e5 = (("uint", 11), ("//", e4, z))
    e6 = (("uint", 12), ("+", e5, e2))
    e3 = (("uint", 6), ("%", e6, (("uint", 6), 32)))
    assert b._code[-1] == ("connect", x, e3)


def test_logop():
    """Test and/or/not"""

    b = _setup()
    x = (("uint", 20), "x")
    y = (("uint", 10), "y")
    z = (("uint", 10), "z")

    def orr(p):
        return (("uint", 1), ("orr", p))

    b.x = b.and_expr(b.y, b.z)
    assert b._code[-1] == ("connect", x, (("uint", 1), ("&", orr(y), orr(z))))

    b.x = b.or_expr(b.y, b.z)
    assert b._code[-1] == ("connect", x, (("uint", 1), ("|", orr(y), orr(z))))

    b.x = b.not_expr(b.y)
    assert b._code[-1] == ("connect", x, (("uint", 1), ("not", orr(y))))

    b.x = b.and_expr(b.y, 10)
    assert b._code[-1] == (
        "connect",
        x,
        (("uint", 1), ("&", orr(y), (("uint", 1), 1))),
    )


def test_bit_slicing():
    """Test var[x:y]"""

    b = _setup()
    b.xx = b.x[3:2]
    xx = (("uint", 11), "xx")
    x = (("uint", 20), "x")

    assert b._code[-1] == (
        "connect",
        xx,
        (("uint", 2), ("bits", x, (("uint", 0), 3), (("uint", 0), 2))),
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

    with raises(IndexError, match=r"Slice MSB must be less or equal to MSB"):
        b.xx = b.x[20]


def test_array_indexing():
    """Test x[y] = z, x = y[z], etc"""

    b = _setup()
    xx = (("uint", 11), "xx")
    x = (("uint", 20), "x")
    s = (("array", 20, (("uint", 10))), "s")
    s2 = (("array", 2, s[0]), "s2")
    y = (("uint", 10), "y")

    b.xx = b.s[b.x]
    assert b._code[-1] == ("connect", xx, (("uint", 10), ("[]", s, x)))

    b.xx = b.s[1]
    assert b._code[-1] == (
        "connect",
        xx,
        (("uint", 10), ("[]", s, (("uint", 1), 1))),
    )

    b.xx = b.s2[1][8]
    assert b._code[-1] == (
        "connect",
        xx,
        (
            ("uint", 10),
            ("[]", (s[0], ("[]", s2, (("uint", 1), 1))), (("uint", 4), 8)),
        ),
    )

    b.s[b.x] = b.y
    assert b._code[-1] == ("connect", (("uint", 10), ("[]", s, x)), y)

    with raises(IndexError, match=r"s\[21\] is out of range \(size=20\)"):
        b.y = b.s[21]

    with raises(TypeError, match=r"is not subscriptable"):
        b.y = b.b[2]

    b.s[b.x] = 3

    b.s2[1] = b.s2[0]

    assert str(b.s2[1]) == "s2[0x1]"
    assert str(b.s2[1][2]) == "s2[0x1][0x2]"

    assert repr(b.s2) == "uint[10][20][2]"


def test_struct_member_access():
    """Test x.a, a.b.c etc"""

    b = _setup()

    b.b.c.a = b.b.d.b
    b.b.c.a = 1

    assert str(b.y) == "y"
    assert str(b.b) == "b"
    assert str(b.b.c.a) == "b.c.a"
    assert str(b.ba[2].f[1].a) == "ba[0x2].f[0x1].a"

    with raises(AttributeError, match=r"has no member bix"):
        b.b.c.bix

    b.p.f[1].b = 1
    with raises(TypeError, match=r"Not allowed to assign to p.f\[0x1\].a"):
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
    assert str(b.inst) == "inst"
    assert str(b.inst.i) == "inst.i"

    b.inst.p.f[1].a = 1
    with raises(
        TypeError, match=r"Not allowed to assign to inst.p.f\[0x1\].b"
    ):
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
        TypeError, match="Cannot assign non-input of instance of mod::inst"
    ):
        b.inst.w = b.b.c
    with raises(TypeError, match="Cannot assign to instance inst"):
        b.inst = 1
    with raises(TypeError, match="Cannot assign to attribute att1"):
        b.att1 = 3
    with raises(TypeError, match="Cannot assign to input"):
        b.y = 3
    r"""
    with raises(
        TypeError,
        match=r"Cannot assign non-equivalent type uint\[10\] to uint\[2\]",
    ):
        b.inst.i = b.y
    """


def test_size_len():
    b = _setup()
    assert len(b.x) == 20
    assert len(b.y) == 10
    assert len(b.s) == 200
    assert len(b.s[0]) == 10
    assert len(b.b) == 20
    assert len(b.ba) == 36
    assert len(b.r) == 20
    z = (b.y + b.z + b.b.c.a) >> 3
    assert len(z) == 12 - 3


def test_sized_values():
    b = _setup()
    z = b.y + uint[20](1)
    assert len(z) == 21
    z = sint[30](-20) + b.xs
    assert len(z) == 31
    with raises(TypeError, match="Cannot create integer constant from struct"):
        b.xs + A()


def test_printf():
    b = _setup()
    b.printf(b.clk, "hello")
    b.printf("hepp %x", b.y)
    b.printf(b.en, "hepp %x %b", b.y, b.x)
    validate(b._db)


def test_assertf():
    b = _setup()
    f = b.assertf
    f(b.clk, b.pred, b.en, "hello")
    f(b.pred, b.en, "hepp %x", b.y)
    f(b.pred, "hepp %x", b.y)
    f(b.clk, b.pred, "hepp %x %b", b.y, b.x)
    validate(b._db)


def test_coverf():
    b = _setup()
    f = b.coverf
    f(b.clk, b.pred, b.en, "hello")
    f(b.pred, b.en, "hepp")
    f(b.pred, "hepp")
    f(b.clk, b.pred, "hepp")
    validate(b._db)


def test_bad_pred_stmt():
    b = _setup()
    with raises(ValueError, match=r"Malformed printf statement"):
        b.printf(None)
    del b._data["clk"]
    with raises(ValueError, match=r"Module mod::mod has no clock"):
        b.printf("no clock")
