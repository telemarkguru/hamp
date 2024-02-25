import hamp._module as mod
from hamp._db import create
from hamp._hwtypes import uint, sint, clock, reset, u1
from hamp._struct import struct
from pytest import raises


def test_create_module():
    m = mod.module("name", db=create())
    assert isinstance(m, mod._Module)
    assert m.name == "name::name"
    with raises(NameError, match=r"Module name::name already defined"):
        mod.module("name", m.db)


def test_clone_module():
    m = mod.module("name", db=create())
    m.x = mod.input(uint[1])
    m.y = mod.wire(uint[2])
    m.clone("name2")
    assert (
        m.db["circuits"]["name"]["name"] == m.db["circuits"]["name2"]["name2"]
    )


def test_member_access_module():
    @struct
    class X:
        a: uint[2]
        b: sint[2]

    m = mod.module("foo", db=create())
    m.x = mod.input(sint[1])
    m["y"] = mod.output(uint[10])
    m["z"] = mod.wire(uint[3][100])
    m.w = mod.input(X)
    assert [x.name for x in m] == ["x", "y", "z", "w"]
    assert m["x"].type == sint[1]
    assert m.y.type == uint[10]
    assert "x" in m
    del m["x"]
    with raises(AttributeError):
        m.x
    assert "x" not in m
    assert len(m.z) == 300
    assert len(m.w) == 4
    assert len(m.w.a) == 2
    assert m.w.a == uint[2]


def test_module_instance():
    db = create()
    sm = mod.module("module::submodule", db=db)
    sm.a = mod.wire(sint[2])
    sm.p = mod.output(uint[1000])
    sm.clk = mod.input(uint[1])
    m = mod.module("module", db=db)
    m.i = sm()
    assert m.i.p.kind == "output"
    m.j = mod.instance("module::submodule")
    with raises(NameError, match="No module named h::higgins defined"):
        m.k = mod.instance("h::higgins")
    assert m["i"].name == "module::submodule"
    assert "k" not in m
    assert "j" in m

    """
    with raises(
        TypeError, match="Member a of module module::submodule is not a port"
    ):
        m.j.a
    """


def test_module_attributes():
    m = mod.module("foo", db=create())
    m.a = mod.attribute(10)
    m.b = mod.attribute({"x": 42})
    assert m["a"].value == 10
    assert m["b"].value == {"x": 42}
    assert len(m.b) == 1


def test_module_code():
    m = mod.module("foo", db=create())

    @m.code
    def blupp(self):
        return 11


def test_module_function():
    m = mod.module("foo", db=create())

    @m.function
    def f(m, a, b):
        return a + b

    assert f(0, 1, 2) == 3


def test_module_add_register():
    m = mod.module("foo", db=create())
    m.clk = mod.input(clock)
    m.rst = mod.input(reset)
    m.reg = mod.register(sint[144], value=0)
    r = m.reg
    assert r.type == sint[144]
    # assert r.clock is m.clk
    # assert r.reset is m.rst
    # assert r.value == 0
    assert len(m.clk) == 1
    assert len(m.rst) == 1
    assert len(m.reg) == 144


def test_module_register_no_clock():
    m = mod.module("foo", db=create())
    with raises(ValueError, match="No clock defined in module foo"):
        m.x = mod.register(uint[2])


def test_module_register_no_reset():
    m = mod.module("foo", db=create())
    m.clk = mod.input(clock)
    with raises(ValueError, match="No reset defined in module foo"):
        m.x = mod.register(uint[2], value=0)


def test_unique_module_name():
    db = create()
    mod.module("foo", db=db)
    m2 = mod.module(mod.unique("foo", db=db), db=db)
    assert m2.name == "foo::foo_1"


def test_module_add_bad_type():
    m = mod.module("foo", db=create())
    with raises(TypeError, match="Cannot add values of type"):
        m.z = 3


def test_module_add_duplicate():
    m = mod.module("foo", db=create())
    m.x = mod.wire(uint[3])
    with raises(KeyError, match="x already defined in module foo"):
        m.x = mod.input(sint[1])


def test_module_not_an_attribute():
    m = mod.module("foo", db=create())
    m.x = mod.wire(uint[3])
    # with raises(KeyError, match="Module member x is not an attribute"):
    #     m["x"]


def test_reserved_name():
    m = mod.module("foo", db=create())
    with raises(NameError, match=r"Name cat is reserved"):
        m.cat = mod.input(u1)


def test_iter_ports():
    m = mod.module("ports", db=create())
    m.a = mod.input(u1)
    m.b = mod.output(u1)
    # assert list(mod.ports(m)) == [m.a, m.b]
