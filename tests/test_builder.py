from hamp._builder import _VarBuilder, _CodeBuilder
from hamp._module import module, input, output, wire
from hamp._hwtypes import uint, sint


def test_code_builder():

    m = module("mod")
    m.x = wire(uint[10])
    m.y = wire(uint[10])
    m.z = wire(uint[10])

    b = _CodeBuilder(m)
    b.x = 3
    assert b.code == [("connect", "x", 3)]

    b.x = b.y + b.z
    with b.if_stmt(b.y == b.z):
        b.x = -1
    with b.elif_stmt(b.y > b.z):
        b.x = 10
    with b.else_stmt():
        b.x = 0

    print(str(b))
