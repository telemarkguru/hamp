from hamp._module import module, wire
from hamp._stdlib import (
    cvt,
    cat,
    pad,
    as_uint,
    as_sint,
    as_clock,
    as_async_reset,
)
from hamp._db import create
from hamp._hwtypes import uint, sint, clock, async_reset


def _setup():
    m = module("test", db=create())
    m.u1 = wire(uint[1])
    m.u2 = wire(uint[2])
    m.u4 = wire(uint[4])
    m.s1 = wire(sint[1])
    m.s2 = wire(sint[2])
    m.s3 = wire(sint[3])
    m.c = wire(clock)
    m.ar = wire(async_reset)
    return m


u1 = (("uint", 1), "u1")
u2 = (("uint", 2), "u2")
u4 = (("uint", 4), "u4")
s1 = (("sint", 1), "s1")
s2 = (("sint", 2), "s2")
s3 = (("sint", 3), "s3")
c = (("clock", 1), "c")
ar = (("async_reset", 1), "ar")


def _uint(n, e):
    return (("uint", n), e)


def _sint(n, e):
    return (("sint", n), e)


def _clock(e):
    return (("clock", 1), e)


def _ar(e):
    return (("async_reset", 1), e)


def test_cvt():
    m = _setup()

    @m.code
    def main(m):
        m.s3 = cvt(m.u2)
        m.s2 = cvt(m.s1)

    assert m.bld._code == [
        ("connect", s3, _sint(3, ("cvt", u2))),
        ("connect", s2, _sint(1, ("cvt", s1))),
    ]


def test_cat():
    m = _setup()

    @m.code
    def main(m):
        m.u4 = cat(m.u1, m.u2)
        m.u4 = cat(m.s2, m.s1)

    assert m.bld._code == [
        ("connect", u4, _uint(3, ("cat", u1, u2))),
        ("connect", u4, _uint(3, ("cat", s2, s1))),
    ]


def test_pad():
    m = _setup()

    @m.code
    def main(m):
        m.u4 = pad(m.u1, 4)
        m.u4 = pad(m.u2, 1)
        m.s3 = pad(m.s1, 3)
        m.s3 = pad(m.s2, 1)

    assert m.bld._code == [
        ("connect", u4, _uint(4, ("pad", u1, 4))),
        ("connect", u4, _uint(2, ("pad", u2, 1))),
        ("connect", s3, _sint(3, ("pad", s1, 3))),
        ("connect", s3, _sint(2, ("pad", s2, 1))),
    ]


def test_as_uint():
    m = _setup()

    @m.code
    def main(m):
        m.u4 = as_uint(m.s3)
        m.u1 = as_uint(m.c)
        m.u1 = as_uint(m.ar)
        m.u2 = as_uint(m.u1)

    assert m.bld._code == [
        ("connect", u4, _uint(3, ("as_uint", s3))),
        ("connect", u1, _uint(1, ("as_uint", c))),
        ("connect", u1, _uint(1, ("as_uint", ar))),
        ("connect", u2, _uint(1, ("as_uint", u1))),
    ]


def test_as_sint():
    m = _setup()

    @m.code
    def main(m):
        m.s2 = as_sint(m.u2)
        m.s1 = as_sint(m.c)
        m.s1 = as_sint(m.ar)
        m.s1 = as_sint(m.s1)

    assert m.bld._code == [
        ("connect", s2, _sint(2, ("as_sint", u2))),
        ("connect", s1, _sint(1, ("as_sint", c))),
        ("connect", s1, _sint(1, ("as_sint", ar))),
        ("connect", s1, _sint(1, ("as_sint", s1))),
    ]


def test_as_clock():
    m = _setup()

    @m.code
    def main(m):
        m.c = as_clock(m.u1)
        m.c = as_clock(m.s1)
        m.c = as_clock(m.c)
        m.c = as_clock(m.ar)

    assert m.bld._code == [
        ("connect", c, _clock(("as_clock", u1))),
        ("connect", c, _clock(("as_clock", s1))),
        ("connect", c, _clock(("as_clock", c))),
        ("connect", c, _clock(("as_clock", ar))),
    ]


def test_as_async_reset():
    m = _setup()

    @m.code
    def main(m):
        m.ar = as_async_reset(m.u1)
        m.ar = as_async_reset(m.s1)
        m.ar = as_async_reset(m.c)
        m.ar = as_async_reset(m.ar)

    assert m.bld._code == [
        ("connect", ar, _ar(("as_async_reset", u1))),
        ("connect", ar, _ar(("as_async_reset", s1))),
        ("connect", ar, _ar(("as_async_reset", c))),
        ("connect", ar, _ar(("as_async_reset", ar))),
    ]
