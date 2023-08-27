import hamp._module as mod
from hamp._hwtypes import uint, sint, clock, reset
import pytest


def test_create_module():
    mod.modules.clear()
    m = mod.module("name")
    assert isinstance(m, mod._Module)
    assert m.name == "name"
    with pytest.raises(NameError, match=r"Redefinition of module name"):
        x = mod.module("name")


def test_clone_module():
    mod.modules.clear()
    m = mod.module("name")
    m.x = mod.input(uint[1])
    m.y = mod.wire(uint[2])
    c = m.clone("name2")
    assert list(mod.modules.keys()) == ["name", "name2"]


def test_member_access_module():
    mod.modules.clear()
    m = mod.module("foo")
    m.x = mod.input(sint[1])
    m["y"] = mod.output(uint[10])
    assert [x for x in m] == ["x", "y"]
    assert m["x"].type == sint[1]
    assert m.y.type == uint[10]
    assert "x" in m
    del m["x"]
    with pytest.raises(KeyError):
        m.x
    assert "x" not in m


def test_module_instance():
    mod.modules.clear()
    sm = mod.module("submodule")
    sm.a = mod.wire(sint[2])
    sm.p = mod.output(uint[1000])
    sm.clk = mod.input(uint[1])
    m = mod.module("module")
    m.i = sm()
    assert isinstance(m.i.p, mod._Port)
    m.j = mod.instance("submodule")
    with pytest.raises(NameError, match="No module named higgins defined"):
        m.k = mod.instance("higgins")
    assert isinstance(m["i"], mod._Instance)
    assert "k" not in m
    assert "j" in m
    with pytest.raises(
        TypeError, match="Member a of module submodule is not a port"
    ):
        m.j.a


def test_module_attributes():
    mod.modules.clear()
    m = mod.module("foo")
    m.a = mod.attribute(10)
    m.b = mod.attribute({"x": 42})
    assert m.attr("a") == 10
    assert m.attr("b") == {"x": 42}


def test_module_code():
    mod.modules.clear()
    m = mod.module("foo")

    @m.code
    def blupp(self):
        return 11

    assert isinstance(m.blupp, mod._ModuleCode)
    assert m.blupp.function(0) == 11


def test_module_function():
    mod.modules.clear()
    m = mod.module("foo")

    @m.function
    def f(m, a, b):
        return a + b

    assert isinstance(m.f, mod._ModuleFunc)
    assert m.f.function(0, 1, 2) == 3


def test_module_add_register():
    mod.modules.clear()
    m = mod.module("foo")
    m.clk = mod.input(clock())
    m.rst = mod.input(reset())
    m.reg = mod.register(sint[144])
    r = m.reg
    assert r.type == sint[144]
    assert r.clock is m.clk
    assert r.reset is m.rst
    assert r.value == 0


def test_module_register_no_clock():
    mod.modules.clear()
    m = mod.module("foo")
    with pytest.raises(ValueError, match="No clock defined in module foo"):
        m.x = mod.register(uint[2])


def test_module_register_no_reset():
    mod.modules.clear()
    m = mod.module("foo")
    m.clk = mod.input(clock())
    with pytest.raises(ValueError, match="No clock defined in module foo"):
        m.x = mod.register(uint[2])


def test_unique_module_name():
    mod.modules.clear()
    m = mod.module("foo")
    m2 = mod.module(mod.unique("foo"))
    assert m2.name == "foo_1"


def test_module_add_bad_type():
    mod.modules.clear()
    m = mod.module("foo")
    with pytest.raises(TypeError, match="Cannot add values of type"):
        m.z = 3


def test_module_add_duplicate():
    mod.modules.clear()
    m = mod.module("foo")
    m.x = mod.wire(uint[3])
    with pytest.raises(KeyError, match="x already defined in module foo"):
        m.x = mod.input(sint[1])


def test_module_not_an_attribute():
    mod.modules.clear()
    m = mod.module("foo")
    m.x = mod.wire(uint[3])
    with pytest.raises(KeyError, match="Module member x is not an attribute"):
        m.attr("x")
