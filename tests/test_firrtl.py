from hamp._firrtl import generate
from hamp._module import module, input, output, wire, register, modules
from hamp._hwtypes import uint, sint, clock, reset, async_reset, sync_reset
from hamp._struct import struct, flip
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
        circuit test :

          module test :
            input x : UInt<1>
            input en : UInt<1>
            output y : SInt<2>

            wire w : UInt<3>

            when en :
                w <= add(x, UInt(1))
            else :
                w <= sub(x, UInt(1))
            y <= add(w, UInt(1))
    """
        ).lstrip()
    )


def test_counter():
    modules.clear()
    u1 = uint[1]
    w = 10

    m = module("test")
    m.clk = input(clock())
    m.rst = input(async_reset())
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
    with open("test.firrtl", "w") as fh:
        print(code, file=fh)
    assert (
        code
        == dedent(
            """
        FIRRTL version 1.1.0
        circuit test :

          module test :
            input clk : Clock
            input rst : AsyncReset
            input en : UInt<1>
            output out : UInt<10>

            reg cnt : UInt<10>, clk with: (reset => (rst, UInt<10>(0))

            when en :
                cnt <= add(cnt, UInt(3))
            out <= cnt
    """
        ).lstrip()
    )


def test_struct():
    modules.clear()
    u1 = uint[1]

    @struct
    class Data:
        x: uint[12]
        y: sint[12]

    @struct
    class Foo:
        valid: u1
        ready: flip(u1)
        data: Data

    m = module("struct")
    m.clk = input(clock())
    m.din = input(Foo)
    m.dout = output(Foo)
    m.x = register(Data, m.clk, False)

    @m.code
    def main(x):
        x.x = x.din.data
        x.dout.data = x.x
        x.dout.valid = x.din.valid
        x.din.ready = x.dout.ready

    code = generate(m)
    assert (
        code
        == dedent(
            """
        FIRRTL version 1.1.0
        circuit struct :

          module struct :
            input clk : Clock
            input din : {valid: UInt<1>, flip ready: UInt<1>, data: {x: UInt<12>, y: SInt<12>}}
            output dout : {valid: UInt<1>, flip ready: UInt<1>, data: {x: UInt<12>, y: SInt<12>}}

            reg x : {x: UInt<12>, y: SInt<12>}, clk

            x <= din.data
            dout.data <= x
            dout.valid <= din.valid
            din.ready <= dout.ready
    """
        ).lstrip()
    )
