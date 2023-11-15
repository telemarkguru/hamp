from hamp._firrtl import generate
from hamp._module import module, input, output, wire, register, modules
from hamp._hwtypes import uint, sint, clock, reset
from textwrap import dedent


def test_simple():
    modules.clear()
    m = module("test")
    m.x = input(uint[1])
    m.y = output(sint[2])
    m.w = wire(uint[3])

    @m.code
    def f(b):
        b.w = b.x + 1
        b.y = b.w + 1

    code = generate(m)
    print(code)
    assert (
        code
        == dedent(
            """
        FIRRTL version 1.1.0
        circuit :
          public module test :
            input x : UInt<1>
            output y : SInt<2>
            wire w : UInt<3>
            connect w, add(x, UInt(1))
            connect y, add(w, UInt(1))
    """
        ).lstrip()
    )
