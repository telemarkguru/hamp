from hamp._firrtl import generate
from hamp._module import module, input, output, wire, register, modules
from hamp._hwtypes import uint, sint, u1, clock, async_reset
from hamp._struct import struct, flip
from os.path import dirname, abspath


_this = dirname(abspath(__file__))


def _generate_and_check(name, *m):
    code = generate(*m)
    with open(f"{_this}/{name}.fir", "w") as fh:
        fh.write(code)
    with open(f"{_this}/{name}_exp.fir") as fh:
        assert fh.read() == code


def test_simple():
    modules.clear()

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

    _generate_and_check("simple", m)


def test_counter():
    modules.clear()
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

    _generate_and_check("counter", m)


def test_struct():
    modules.clear()

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

    _generate_and_check("struct", m)


def test_ops():
    modules.clear()

    m = module("ops")
    m.a = input(uint[8])
    m.b = input(uint[8])
    m.c = input(sint[8])
    m.d = input(sint[8])
    m.x = output(uint[9][2])
    m.y = output(sint[9][2])
    m.z = output(sint[9][2])

    @m.code
    def main(x):  # pragma: no cover
        x.x[0] = x.a >> x.b
        x.x[1] = x.a << x.b
        x.y[0] = x.c >> x.b
        x.y[1] = x.c << x.b
        x.z[0] = x.c << 3
        x.z[1] = x.c >> 2

    _generate_and_check("ops", m)


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
        x.z = x.cat(x.a[x.x][x.y], x.b)

    _generate_and_check("index", m)


def test_instantiation():
    modules.clear()

    @struct
    class Data:
        x: uint[2]
        y: sint[3]

    m = module("mux")
    m.a = input(Data)
    m.b = input(Data)
    m.x = output(Data)
    m.sel = input(uint[1])

    @m.code
    def main(m):  # pragma: no cover
        if m.sel:
            m.x = m.b
        else:
            m.x = m.a

    mux = m

    m = module("mux4")
    m.a = input(Data[4])
    m.x = output(Data)
    m.sel = input(uint[2])

    m.m1 = mux()
    m.m2 = mux()
    m.m3 = mux()

    @m.code
    def main2(m):  # pragma: no cover
        m.m1.a = m.a[0]
        m.m1.b = m.a[1]
        m.m1.sel = m.sel[0]
        m.m2.a = m.a[2]
        m.m2.b = m.a[3]
        m.m2.sel = m.sel[0]
        m.m3.a = m.m1.x
        m.m3.b = m.m2.x
        m.m3.sel = m.sel[1]
        m.x = m.m3.x

    _generate_and_check("mux4", m, mux)


def test_logic_expr():
    modules.clear()

    m = module("logexp")
    m.a = input(uint[3])
    m.b = input(sint[4])
    m.c = input(uint[1])
    m.x = output(uint[1])
    m.y = output(uint[3])

    @m.code
    def main(m):  # pragma: no cover
        m.x = m.a and m.b and m.c
        m.y = 0
        if not m.a:
            m.y = 1
        elif m.a or m.c:
            m.y = 2
        elif m.b:
            m.y = 3

    _generate_and_check("logexp", m)


def test_composit_data_types():
    modules.clear()

    @struct
    class C:
        r: sint[32]
        i: sint[32]

    @struct
    class Pos:
        x: C
        y: C
        z: C[4]
        g: C[4][2]

    @struct
    class R:
        a: Pos
        b: Pos
        c: uint[2]

    m = module("data_types")
    m.a = input(C)
    m.c = input(Pos)
    m.c2 = input(Pos[2])
    m.r = input(R)
    m.r3 = input(R[3])
    m.z = output(C[3])
    m.zsel = input(uint[2])
    m.gsel = input(uint[1])
    m.rsel = input(uint[1])

    @m.code
    def main(m):  # pragma: no cover
        m.z[0] = m.r3[m.rsel].a.g[m.gsel][m.zsel]
        m.z[1] = m.r.b.z[m.zsel]
        m.z[2] = m.c2[m.rsel].x

    _generate_and_check("data_types", m)
