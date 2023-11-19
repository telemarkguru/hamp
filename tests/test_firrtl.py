from hamp._firrtl import generate
from hamp._module import module, input, output, wire, register, modules
from hamp._hwtypes import uint, sint, clock, async_reset
from hamp._struct import struct, flip
from os.path import dirname, abspath


_this = dirname(abspath(__file__))


def _generate_and_check(m, name):
    code = generate(m)
    with open(f"{_this}/{name}.fir", "w") as fh:
        fh.write(code)
    with open(f"{_this}/{name}_exp.fir") as fh:
        assert fh.read() == code


def test_simple():
    modules.clear()
    u1 = uint[1]

    m = module("test")
    m.x = input(u1)
    m.en = input(u1)
    m.y = output(uint[2])
    m.w = wire(uint[3])

    @m.code
    def f(b):  # pragma: no cover
        if b.en:
            b.w = b.x + 1
        else:
            b.w = b.x - 1
        b.y = b.w + 1

    _generate_and_check(m, "simple")


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
    def inc(x, delta=1):  # pragma: no cover
        x.cnt = x.cnt + delta

    @m.code
    def main(x):  # pragma: no cover
        if x.en:
            x.inc(x, 3)
        x.out = x.cnt

    _generate_and_check(m, "counter")


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
    def main(x):  # pragma: no cover
        x.x = x.din.data
        x.dout.data = x.x
        x.dout.valid = x.din.valid
        x.din.ready = x.dout.ready

    _generate_and_check(m, "struct")
