"""Standard functions"""


from ._builder import _OneOpExpr, _TwoOpExpr, _reduce2, _IntExpr, _Expr
from ._hwtypes import _HWType


class _CvtExpr(_OneOpExpr):
    op = "cvt"

    def infer_type(self, v1) -> _HWType:
        if v1.type.signed:
            return v1.expr[0]
        return ("sint", len(v1) + 1)


class _CatExpr(_TwoOpExpr):
    op = "cat"

    def infer_type(self, v1, v2) -> _HWType:
        size = len(v1) + len(v2)
        return ("uint", size)


def cvt(expr: _IntExpr) -> _OneOpExpr:
    """Convert to signed"""
    return _CvtExpr(expr)


def cat(*ops: _IntExpr) -> _TwoOpExpr:
    """Concatenate"""
    return _reduce2(_CatExpr, *ops)


def pad(op: _IntExpr, bits: int) -> _IntExpr:
    nbits = max(bits, len(op))
    return _IntExpr((op.new_type(nbits), ("pad", op.expr, bits)))


def as_uint(op: _IntExpr) -> _IntExpr:
    """Interpret as uint"""
    if op.expr[0][0] in ("uint", "sint", "clock", "reset", "async_reset"):
        return _IntExpr((("uint", len(op)), ("as_uint", op.expr)))
    raise TypeError(f"Cannot interpret {str(op.type)} as uint")


def as_sint(op: _IntExpr) -> _IntExpr:
    """Interpret as sint"""
    if op.expr[0][0] in ("uint", "sint", "clock", "reset", "async_reset"):
        return _IntExpr((("sint", len(op)), ("as_sint", op.expr)))
    raise TypeError(f"Cannot interpret {str(op.type)} as sint")


def as_clock(op: _IntExpr) -> _Expr:
    """Interpret as clock"""
    if op.expr[0] in (
        ("uint", 1),
        ("sint", 1),
        ("clock", 1),
        ("reset", 1),
        ("async_reset", 1),
    ):
        return _Expr((("clock", 1), ("as_clock", op.expr)))
    raise TypeError(f"Cannot interpret {str(op.type)} as clock")


def as_async_reset(op: _IntExpr) -> _Expr:
    """Interpret as async_reset"""
    if op.expr[0] in (
        ("uint", 1),
        ("sint", 1),
        ("clock", 1),
        ("reset", 1),
        ("async_reset", 1),
    ):
        return _Expr((("async_reset", 1), ("as_async_reset", op.expr)))
    raise TypeError(f"Cannot interpret {str(op.type)} as async_reset")
