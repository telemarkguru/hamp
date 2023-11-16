from hamp._firrtl import generate
from hamp._module import module, input, output, wire, register, modules
from hamp._hwtypes import uint, sint, clock, reset
from textwrap import dedent


def test_simple():
    modules.clear()
    u1 = uint[1]

    m = module("test")
    m.x = input(u1)
    m.en = input(u1)
    m.y = output(sint[2])
    m.w = wire(uint[3])

    @m.code
    def f(b):
        if b.en:
            b.w = b.x + 1
        else:
            b.w = b.x - 1
        b.y = b.w + 1

    code = generate(m)
    assert (
        code
        == dedent(
            """
        FIRRTL version 1.1.0
        circuit :

          public module test :
            input x : UInt<1>
            input en : UInt<1>
            output y : SInt<2>

            wire w : UInt<3>

            when en :
                connect w, add(x, UInt(1))
            else :
                connect w, sub(x, UInt(1))
            connect y, add(w, UInt(1))
    """
        ).lstrip()
    )


def test_counter():
    modules.clear()
    u1 = uint[1]
    w = 10

    m = module("test")
    m.clk = input(clock())
    m.rst = input(reset())
    m.en = input(u1)
    m.out = output(uint[w])
    m.cnt = register(uint[w], m.clk, m.rst)

    @m.function
    def inc(x, delta=1):
        x.cnt = x.cnt + delta

    @m.code
    def main(x):
        if x.en:
            x.inc(x, 3)
        x.out = x.cnt

    code = generate(m)
    assert (
        code
        == dedent(
            """
        FIRRTL version 1.1.0
        circuit :

          public module test :
            input clk : Clock
            input rst : Reset
            input en : UInt<1>
            output out : UInt<10>

            regreset cnt : UInt<10>, clk, rst, 0

            when en :
                connect cnt, add(cnt, UInt(3))
            connect out, cnt
    """
        ).lstrip()
    )
