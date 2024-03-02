from hamp._firrtl import firrtl, verilog
from hamp._module import module, input, output, wire, register
from hamp._hwtypes import uint, sint, u1, clock, async_reset
from hamp._struct import struct, flip
from hamp._memory import memory, wmask_type
from hamp._db import validate, create
from hamp._stdlib import cat
from os.path import dirname, abspath
from pprint import pprint


_this = dirname(abspath(__file__))


def _generate_and_check(name, *m):  # pragma: no cover
    db = m[0].db
    with open(f"{_this}/{name}.db", "w") as fh:
        pprint(db, stream=fh, sort_dicts=False, indent=4)
    validate(db)
    try:
        verilog(db=db, name=name, odir=_this)
    except FileNotFoundError:
        firrtl(db=db, name=name, odir=_this)
    with open(f"{_this}/{name}.fir") as fh:
        code = fh.read()
    with open(f"{_this}/{name}_exp.fir") as fh:
        assert fh.read() == code


def test_simple():
    m = module("test", db=create())
    m.x = input(u1)
    m.en = input(u1)
    m.y = output(uint[4])
    m.w = wire(uint[3])

    @m.code
    def f(b):
        if b.en:
            b.w = b.x + 1
        else:
            b.w = b.x - 1
        b.y = b.w + 1

    _generate_and_check("simple", m)


def test_counter():
    w = 10

    m = module("test", db=create())
    m.clk = input(clock)
    m.rst = input(async_reset)
    m.en = input(u1)
    m.out = output(uint[w])
    m.cnt = register(uint[w], m.clk, m.rst, value=0)

    def add2(x):
        return x + 2

    @m.function
    def inc(x, delta=1):
        x.cnt = (x.cnt + delta)[w - 1 : 0]

    @m.code
    def main(x):
        if x.en:
            inc(x, add2(1))
        x.out = x.cnt

    _generate_and_check("counter", m)


def test_struct():
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

    m = module("struct", db=create())
    m.clk = input(clock)
    m.din = input(Foo)
    m.dout = output(Foo)
    m.sel = input(uint[2])
    m.x = register(Data, m.clk)
    m.y = register(Data[3], m.clk)

    @m.code
    def main(x):
        x.x = x.din.data
        x.y[x.sel] = x.din.data
        x.dout.data = x.x
        x.dout.data2 = x.y
        x.dout.valid = x.din.valid
        x.din.ready = x.dout.ready

    _generate_and_check("struct", m)


def test_ops():
    m = module("ops", db=create())
    m.a = input(uint[8])
    m.b = input(uint[8])
    m.c = input(sint[8])
    m.d = input(sint[8])
    m.x = output(uint[9][2])
    m.y = output(sint[263][2])
    m.z = output(sint[11][2])

    @m.code
    def main(x):
        x.x[0] = x.a >> x.b
        x.x[1] = (x.a << x.b)[8:0]
        x.y[0] = x.c >> x.b
        x.y[1] = x.c << x.b
        x.z[0] = x.c << 3
        x.z[1] = x.c >> 2

    _generate_and_check("ops", m)


def test_index():
    m = module("index", db=create())
    m.a = input(sint[8][4][3])
    m.x = input(uint[2])
    m.y = input(uint[2])
    m.z = output(uint[18])
    m.b = input(sint[10])

    @m.code
    def main(x):
        x.z = cat(x.a[x.x][x.y], x.b)

    _generate_and_check("index", m)


def test_instantiation():
    db = create()

    @struct
    class Data:
        x: uint[2]
        y: sint[3]

    m = module("mux", db=db)
    m.a = input(Data)
    m.b = input(Data)
    m.x = output(Data)
    m.sel = input(uint[1])

    @m.code
    def main(m):
        if m.sel:
            m.x = m.b
        else:
            m.x = m.a

    mux = m

    m = module("mux4", db=db)
    m.a = input(Data[4])
    m.x = output(Data)
    m.sel = input(uint[2])

    m.m1 = mux()
    m.m2 = mux()
    m.m3 = mux()

    @m.code
    def main2(m):
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
    m = module("logexp", db=create())
    m.a = input(uint[3])
    m.b = input(sint[4])
    m.c = input(uint[1])
    m.x = output(uint[1])
    m.y = output(uint[3])

    @m.code
    def main(m):
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

    m = module("data_types", db=create())
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
    def main(m):
        m.z[0] = m.r3[m.rsel].a.g[m.gsel][m.zsel]
        m.z[1] = m.r.b.z[m.zsel]
        m.z[2] = m.c2[m.rsel].x

    _generate_and_check("data_types", m)


def test_functional():
    m = module("functional")
    m.i = input(uint[10][5])
    m.o = output(uint[14])
    m.c = output(uint[4])

    @m.code
    def main(m):
        m.o = sum(m.i)
        m.c = sum(m.i[0])

    _generate_and_check("functional", m)


def test_composit_register():
    @struct
    class C:
        r: sint[20]
        i: sint[20]

    m = module("composit_register", db=create())
    m.clk = input(clock)
    m.rst = input(async_reset)
    m.data = register(C)  # , value=dict(r=0, i=0))
    m.r = input(sint[20])
    m.i = input(sint[20])
    m.en = input(u1)
    m.x = output(sint[40])

    @m.code
    def main(m):
        if m.en:
            m.data.r = m.r
            m.data.i = m.i
        m.x = m.data.r * m.data.i

    _generate_and_check("composit_register", m)


def test_memory():
    db = create()

    @struct
    class D:
        a: uint[2]
        b: sint[3]
        c: sint[3][2]

    mask_t = wmask_type(D)

    m = module("memories", db=db)
    m.clk = input(clock)
    m.addr = input(uint[8])
    m.we = input(u1)
    m.re = input(u1)
    m.ce = input(u1)
    m.wmode = input(u1)
    m.din = input(D[2])
    m.dout = output(D[2])
    m.ram = memory(D, 256, ["r1"], ["w1"], ["rw1"], db=db)

    m.wmask = wire(mask_t)

    @m.code
    def main(m):
        r1 = m.ram.r1
        r1.en = m.re
        r1.clk = m.clk
        r1.addr = m.addr
        m.dout[0] = r1.data

        w1 = m.ram.w1
        w1.en = m.we
        w1.clk = m.clk
        w1.addr = m.addr
        w1.data = m.din[0]
        w1.mask = m.wmask
        m.wmask.a = 1
        m.wmask.b = 1
        m.wmask.c[0] = 1
        m.wmask.c[1] = 1

        rw1 = m.ram.rw1
        rw1.en = m.ce
        rw1.clk = m.clk
        rw1.addr = m.addr
        rw1.wmode = m.wmode
        rw1.wdata = m.din[1]
        rw1.wmask = m.wmask
        m.dout[1] = rw1.rdata

    _generate_and_check("memories", m)
