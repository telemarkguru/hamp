from hamp._firrtl import generate
from hamp._module import module, input, output, wire, register, modules
from hamp._hwtypes import uint, sint, clock, async_reset
from hamp._struct import struct, flip
from hamp._stdlib import cat
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

    def add2(x):
        return x + 2

    @m.function
    def inc(x, delta=1):  # pragma: no cover
        x.cnt = x.cnt + delta

    @m.code
    def main(x):  # pragma: no cover
        if x.en:
            x.inc(x, add2(1))
        x.out = x.cnt

    _generate_and_check(m, "counter")


def test_struct():
    modules.clear()
    u1 = uint[1]

    @struct
    class Data:
        x: uint[12]
        y: sint[12][3]

    @struct
    class Foo:
        valid: u1
        ready: flip(u1)
        data: Data
        data2: Data[3]

    m = module("struct")
    m.clk = input(clock())
    m.din = input(Foo)
    m.dout = output(Foo)
    m.sel = input(uint[2])
    m.x = register(Data, m.clk, False)
    m.y = register(Data[3], m.clk, False)

    @m.code
    def main(x):  # pragma: no cover
        x.x = x.din.data
        x.y[x.sel] = x.din.data
        x.dout.data = x.x
        x.dout.data2 = x.y
        x.dout.valid = x.din.valid
        x.din.ready = x.dout.ready

    _generate_and_check(m, "struct")


def test_ops():
    modules.clear()

    m = module("ops")
    m.a = input(uint[8])
    m.b = input(uint[8])
    m.c = input(sint[8])
    m.d = input(sint[8])
    m.x = output(uint[9][2])
    m.y = output(sint[9][2])

    @m.code
    def main(x):  # pragma: no cover
        x.x[0] = x.a >> x.b
        x.x[1] = x.a << x.b
        x.y[0] = x.c >> x.b
        x.y[1] = x.c << x.b

    _generate_and_check(m, "ops")


def test_index():
    modules.clear()

    m = module("index")
    m.a = input(sint[8][4][3])
    m.x = input(uint[2])
    m.y = input(uint[2])
    m.z = output(uint[18])
    m.b = input(sint[10])

    @m.code
    def main(x):  # pragma: no cover
        x.z = cat(x.a[x.x][x.y], x.b)

    _generate_and_check(m, "index")
