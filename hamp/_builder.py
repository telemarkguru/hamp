"""Code builder"""

from contextlib import contextmanager
from enum import Enum
from typing import Union, Tuple, Any, Type
from ._db import MODULE, DB
from ._hwtypes import (
    equal,
    _HWType,
)
from ._show import show_type, show_expr
from ._struct import member, flipped


OpType = Union["_IntExpr", int]


class _Expr:
    """Expression"""

    type: _HWType
    expr: tuple

    def __init__(self, expr: tuple):
        self.type = _HWType(expr[0])
        self.expr = expr

    def __len__(self):
        return len(self.type)


class _IntExpr(_Expr):
    """Integer Expression"""

    def new_type(self, size) -> tuple:
        return (self.expr[0][0], size)

    def _chk_slice(self, slice):
        error = None
        if not (isinstance(slice.start, int) and isinstance(slice.stop, int)):
            error = "Slice indexes must be integer constants"
        elif slice.step is not None:
            error = "Step in slice index not allowed"
        elif slice.stop > slice.start:
            error = "Slice MSB must be equal to or larger than LSB"
        elif slice.stop >= len(self):
            error = "Slice MSB must be less or equal to MSB"
        if error:
            slicestr = str(slice)[6:-1].replace(", ", ":")
            raise IndexError(f"{error}: {show_expr(self.expr)}[{slicestr}]")

    def __getitem__(self, idx) -> "_Expr":
        if isinstance(idx, int):
            idx = slice(idx, idx)
        if isinstance(idx, slice):
            self._chk_slice(idx)
            size = idx.start - idx.stop + 1
            return _BitsExpr(self, idx.start, idx.stop, size)
        else:
            raise TypeError(f"Expected constant bit-slice, not {idx}")

    def __add__(self, value: OpType) -> "_Expr":
        return _AddExpr(self, value)

    def __radd__(self, value: OpType) -> "_Expr":
        return _AddExpr(value, self)

    def __sub__(self, value: OpType) -> "_Expr":
        return _SubExpr(self, value)

    def __rsub__(self, value: OpType) -> "_Expr":
        return _SubExpr(value, self)

    def __mul__(self, value: OpType) -> "_Expr":
        return _MulExpr(self, value)

    def __rmul__(self, value: OpType) -> "_Expr":
        return _MulExpr(value, self)

    def __mod__(self, value: OpType) -> "_Expr":
        return _ModExpr(self, value)

    def __floordiv__(self, value: OpType) -> "_Expr":
        return _DivExpr(self, value)

    def __rfloordiv__(self, value: OpType) -> "_Expr":
        return _DivExpr(value, self)

    def __or__(self, value: OpType) -> "_Expr":
        return _OrExpr(self, value)

    def __ror__(self, value: OpType) -> "_Expr":
        return _OrExpr(value, self)

    def __and__(self, value: OpType) -> "_Expr":
        return _AndExpr(self, value)

    def __rand__(self, value: OpType) -> "_Expr":
        return _AndExpr(value, self)

    def __xor__(self, value: OpType) -> "_Expr":
        return _XorExpr(self, value)

    def __rxor__(self, value: OpType) -> "_Expr":
        return _XorExpr(value, self)

    def __invert__(self) -> "_Expr":
        return _NotExpr(self)

    def __lshift__(self, value: OpType) -> "_Expr":
        return _LShiftExpr(self, value, False)

    def __rlshift__(self, value: OpType) -> "_Expr":
        return _LShiftExpr(value, self, False)

    def __rshift__(self, value: OpType) -> "_Expr":
        return _RShiftExpr(self, value, False)

    def __rrshift__(self, value: OpType) -> "_Expr":
        return _RShiftExpr(value, self, False)

    def __neg__(self) -> "_Expr":
        return _NegExpr(self)

    def __pos__(self) -> "_Expr":
        return self

    def __eq__(self, value: OpType) -> "_Expr":  # type: ignore[override]
        return _EqExpr(self, value)

    def __ge__(self, value: OpType) -> "_Expr":  # type: ignore[override]
        return _GeExpr(self, value)

    def __gt__(self, value: OpType) -> "_Expr":  # type: ignore[override]
        return _GtExpr(self, value)

    def __le__(self, value: OpType) -> "_Expr":  # type: ignore[override]
        return _LeExpr(self, value)

    def __lt__(self, value: OpType) -> "_Expr":  # type: ignore[override]
        return _LtExpr(self, value)

    def __ne__(self, value: OpType) -> "_Expr":  # type: ignore[override]
        return _NeExpr(self, value)


class _ConstExpr(_IntExpr):
    def __init__(self, value: int, signed: bool, size: int = 0):
        kind = "sint" if signed else "uint"
        if size == 0:
            size = value.bit_length()
        super().__init__(((kind, size), value))

    @property
    def value(self):
        return self.expr[1]


def _infer_int(type: tuple, value: int) -> _ConstExpr:
    k = type[0]
    if k not in ("uint", "sint"):
        raise TypeError(f"Cannot infer integer for type {k}")
    return _ConstExpr(value, k == "sint", type[1])


class _BitsExpr(_IntExpr):
    """bits, a.k.a. [msb:lsb]"""

    def __init__(self, v1: _IntExpr, start: int, stop: int, size: int):
        super().__init__(
            (
                ("uint", size),
                ("bits", v1.expr, (("uint", 0), start), (("uint", 0), stop)),
            )
        )


class _TwoOpExpr(_IntExpr):
    op: str

    def __init__(self, v1: OpType, v2: OpType, v2signed=None):
        assert isinstance(v1, (int, _IntExpr))
        assert isinstance(v2, (int, _IntExpr))
        if isinstance(v1, _IntExpr):
            s1 = v1.type.signed
            if isinstance(v2, int):
                if v2signed is not None:
                    s1 = v2signed
                v2 = _ConstExpr(v2, s1)
        if isinstance(v2, _IntExpr):
            s2 = v2.type.signed
            if isinstance(v1, int):
                v1 = _ConstExpr(v1, s2)
        assert isinstance(v1, _IntExpr)
        assert isinstance(v2, _IntExpr)
        self.check_types(v1, v2)
        super().__init__(
            (self.infer_type(v1, v2), (self.op, v1.expr, v2.expr))
        )

    def check_types(self, v1, v2):
        if v1.type.signed != v2.type.signed:
            raise TypeError(
                "Both operands must have same sign "
                f"{self.op}: {v1.type} {v2.type}"
            )

    def infer_type(self, v1, v2) -> tuple:  # pragma: no cover
        assert False


class _AddExpr(_TwoOpExpr):
    op = "+"

    def infer_type(self, v1, v2) -> tuple:
        size = max(len(v1), len(v2)) + 1
        return v1.new_type(size)


class _SubExpr(_TwoOpExpr):
    op = "-"

    def infer_type(self, v1, v2) -> tuple:
        size = max(len(v1), len(v2)) + 1
        return v1.new_type(size)


class _MulExpr(_TwoOpExpr):
    op = "*"

    def infer_type(self, v1, v2) -> tuple:
        size = len(v1) + len(v2)
        return v1.new_type(size)


class _ModExpr(_TwoOpExpr):
    op = "%"

    def infer_type(self, v1, v2) -> tuple:
        size = min(len(v1), len(v2))
        return v1.new_type(size)


class _DivExpr(_TwoOpExpr):
    op = "//"

    def infer_type(self, v1, v2) -> tuple:
        size = len(v1) + v1.type.signed
        return v1.new_type(size)


class _OrExpr(_TwoOpExpr):
    op = "|"

    def infer_type(self, v1, v2) -> tuple:
        size = max(len(v1), len(v2))
        return ("uint", size)


class _AndExpr(_TwoOpExpr):
    op = "&"

    def infer_type(self, v1, v2) -> tuple:
        size = max(len(v1), len(v2))
        return ("uint", size)


class _XorExpr(_TwoOpExpr):
    op = "^"

    def infer_type(self, v1, v2) -> tuple:
        size = max(len(v1), len(v2))
        return ("uint", size)


class _LShiftExpr(_TwoOpExpr):
    op = "<<"

    def check_types(self, v1, v2):
        if v2.type.signed:
            raise TypeError(
                "Shift amount must be an unsigned value"
                f"{self.op}: {v1.type} {v2.type}"
            )

    def infer_type(self, v1, v2) -> tuple:
        if isinstance(v2, _ConstExpr):
            size = len(v1) + v2.value
        else:
            size = len(v1) + 2 ** len(v1) - 1
        return v1.new_type(size)


class _RShiftExpr(_TwoOpExpr):
    op = ">>"

    def check_types(self, v1, v2):
        if v2.type.signed:
            raise TypeError(
                "Shift amount must be an unsigned value"
                f"{self.op}: {v1.type} {v2.type}"
            )

    def infer_type(self, v1, v2) -> tuple:
        if isinstance(v2, _ConstExpr):
            size = max(len(v1) - v2.value, 1)
        else:
            size = len(v1)
        return v1.new_type(size)


class _CmpExpr(_TwoOpExpr):
    def infer_type(self, v1, v2) -> tuple:
        return ("uint", 1)


class _EqExpr(_CmpExpr):
    op = "=="


class _GeExpr(_CmpExpr):
    op = ">="


class _GtExpr(_CmpExpr):
    op = ">"


class _LeExpr(_CmpExpr):
    op = "<="


class _LtExpr(_CmpExpr):
    op = "<"


class _NeExpr(_CmpExpr):
    op = "!="


def _reduce2(cls: Type[_TwoOpExpr], *ops: OpType) -> _IntExpr:
    assert len(ops) >= 2
    if len(ops) == 2:
        return cls(ops[0], ops[1])
    return cls(ops[0], _reduce2(cls, *ops[1:]))


class _OneOpExpr(_IntExpr):
    op: str

    def __init__(self, v1: OpType):
        assert isinstance(v1, _Expr)
        t = self.infer_type(v1)
        super().__init__((t, (self.op, v1.expr)))

    def infer_type(self, v1) -> tuple:  # pragma: no cover
        assert False


class _NegExpr(_OneOpExpr):
    op = "neg"

    def infer_type(self, v1) -> tuple:
        return ("sint", len(v1) + 1)


class _NotExpr(_OneOpExpr):
    op = "not"

    def infer_type(self, v1) -> tuple:
        return ("uint", len(v1))


class _OrrExpr(_OneOpExpr):
    op = "orr"

    def infer_type(self, v1) -> tuple:
        return ("uint", 1)


class Access(Enum):
    ANY = 0
    WR = 1
    RD = 2


def _vartype(item: tuple, access: Access, builder: "_CodeBuilder") -> "_Var":
    kind = item[0][0]
    if kind == "struct":
        return _StructVar(item, access, builder)
    elif kind == "array":
        return _ArrayVar(item, access, builder)
    elif kind == "instance":
        return _InstanceVar(item, access, builder)
    return _IntVarExpr(item, builder)


class _Var:
    expr: tuple
    _builder: "_CodeBuilder"
    _type: _HWType
    _access: Access

    def __init__(
        self,
        expr: tuple,
        access: Access,
        builder: "_CodeBuilder",
    ):
        self.expr = expr
        self._builder = builder
        self._type = _HWType(expr[0])
        self._access = access

    def __len__(self):
        return len(self._type)

    def __str__(self) -> str:
        return show_expr(self.expr)

    def __repr__(self) -> str:
        return show_type(self.expr[0])


class _IntVarExpr(_IntExpr, _Var):
    def __init__(
        self,
        expr: tuple,
        builder: "_CodeBuilder",
    ):
        _IntExpr.__init__(self, expr)
        _Var.__init__(self, expr, Access.RD, builder)


def _flip_access(a, flip):
    if flip:
        if a == Access.WR:
            return Access.RD
        if a == Access.RD:
            return Access.WR
    return a


class _StructVar(_Var):
    _VARS = set(("expr", "_builder", "_type", "_access"))
    _access: Access

    def __getattr__(self, name: str) -> _Var:
        item = member(self._type, name)
        access = _flip_access(self._access, flipped(self._type, name))
        return _vartype(
            (item.expr, (".", self.expr, name)), access, self._builder
        )

    def __setattr__(self, name: str, value: Union[_Expr, _Var, int]):
        if name in _StructVar._VARS:
            super().__setattr__(name, value)
            return
        access = _flip_access(self._access, flipped(self._type, name))
        if access == Access.RD:
            raise TypeError(f"Not allowed to assign to {str(self)}.{name}")
        item = member(self._type, name)
        if isinstance(value, int):
            value = _infer_int(item.expr, value)
        if not equal(value.expr[0], item.expr, False):
            raise TypeError(
                "Cannot assign non-equivalent type "
                f"{show_type(value.expr[0])} to {show_type(item.expr)}"
            )
        self._builder._code.append(
            ("connect", (item.expr, (".", self.expr, name)), value.expr)
        )


class _ArrayVar(_Var):
    def _chk_idx(self, idx: int) -> _ConstExpr:
        size = self._type.size
        if not 0 <= idx < size:
            raise IndexError(
                f"{str(self)}[{idx}] is out of range (size={size})"
            )
        return _ConstExpr(idx, False)

    def __getitem__(self, idx: OpType) -> _Var:
        if isinstance(idx, slice):
            # TODO: Add vector slice support
            raise TypeError(f"{str(self)} is not a bit-vector")
        if isinstance(idx, int):
            idx = self._chk_idx(idx)
        return _vartype(
            (self._type.type.expr, ("[]", self.expr, idx.expr)),
            self._access,
            self._builder,
        )

    def __setitem__(self, idx: OpType, value: OpType) -> None:
        type = self._type.type
        if isinstance(idx, int):
            idx = self._chk_idx(idx)
        if self._access == Access.RD:
            raise TypeError(f"Not allowed to assign to {str(self)}[]")
        if isinstance(value, int):
            value = _ConstExpr(value, type.signed)
        if not equal(type.expr, value.expr[0], False):
            raise TypeError(
                "Cannot assign non-equivalent type "
                f"{show_type(value.expr[0])} to {show_type(type.expr)}"
            )
        self._builder._code.append(
            (
                "connect",
                (self._type.type.expr, ("[]", self.expr, idx.expr)),
                value.expr,
            )
        )


class _InstanceVar(_Var):
    _VARS = set(("expr", "_builder", "_type", "_access", "_module"))
    _module = None

    def _get_module(self):
        db = self._builder._db
        cn, mn = self.expr[0][1:3]
        m = db["circuits"][cn][mn]
        self._module = m
        return m

    def _lookup(self, name: str) -> tuple:
        if (m := self._module) is None:
            m = self._get_module()
        if (item := m["data"].get(name)) is None:
            cn, mn = self.expr[0][1:3]
            raise AttributeError(f"Module {cn}::{mn} has no member {name}")
        return item

    def __getattr__(self, name: str) -> _Var:
        item = self._lookup(name)
        kind = item[0]
        if kind == "input":
            return _vartype(
                (item[1], (".", self.expr, name)), Access.WR, self._builder
            )
        if kind == "output":
            return _vartype(
                (item[1], (".", self.expr, name)), Access.RD, self._builder
            )
        cn, mn = self.expr[0][1:3]
        raise TypeError(f"Cannot access {name} in instance of {cn}::{mn}")

    def __setattr__(self, name: str, value: Union[_Expr, int]):
        if name in _InstanceVar._VARS:
            super().__setattr__(name, value)
            return
        item = self._lookup(name)
        kind = item[0]
        if kind == "input":
            if isinstance(value, int):
                value = _infer_int(item[1], value)
            if not equal(item[1], value.expr[0], False):
                raise TypeError(
                    "Cannot assign non-equivalent type "
                    f"{show_type(value.expr[0])} to {show_type(item[1])}"
                )
            self._builder._code.append(
                ("connect", (item[1], (".", self.expr, name)), value.expr)
            )
            return
        cn, mn = self.expr[0][1:3]
        raise TypeError(f"Cannot assign non-input of instance of {cn}::{mn}")


def _logic_value(value: OpType) -> _IntExpr:
    if isinstance(value, _Expr):
        type = value.type
        kind = type.kind
        if kind == "uint" and len(type) == 1:
            return value
        return _OrrExpr(value)
    return _ConstExpr(int(bool(value)), False, 1)


CodeListItemType = Tuple[Any, ...]


class _CodeBuilder:
    """Represents a module when generating code"""

    _name: str
    _module: MODULE
    _data: dict[str, tuple]
    _code: list[tuple]
    _db: DB

    _VARS = set(("_name", "_module", "_data", "_db", "_code"))

    def __init__(self, name: str, module: MODULE, db: DB):
        self._name = name
        self._module = module
        self._data = module["data"]
        self._db = db
        self._code = module["code"]

    def __getattr__(self, name: str) -> _Var:
        if not (item := self._data.get(name)):
            raise AttributeError(f"Module {self._name} has no member {name}")
        kind = item[0]
        access = Access.ANY
        if kind == "input":
            access = Access.RD
        elif kind == "output":
            access = Access.WR
        return _vartype((item[1], name), access, self)

    def __setattr__(self, name: str, value) -> None:
        """Assign value"""
        if name in _CodeBuilder._VARS:
            super().__setattr__(name, value)
            return
        if name not in self._data:
            raise AttributeError(f"Module {self._name} has no member {name}")
        item = self._data[name]
        kind = item[0]
        if kind in ("output", "wire", "register"):
            if isinstance(value, int):
                value = _infer_int(item[1], value)
            if not equal(item[1], value.expr[0], sizes=False):
                raise TypeError(
                    "Cannot assign non-equivalent type "
                    f"{show_type(value.expr[0])} to {show_type(item[1])}"
                )
            self._code.append(("connect", (item[1], name), value.expr))
        else:
            raise TypeError(f"Cannot assign to {kind} {name}")

    def __str__(self) -> str:
        text = []

        def f(code, indent=""):
            for c in code:
                match c:
                    case ("when", expr, stmnts):
                        text.append(f"{indent}('when', {expr}, (")
                        f(stmnts, indent + "    ")
                        text.append(f"{indent}))")
                    case ("else-when", expr, stmnts):
                        text.append(f"{indent}('else-when', {expr}, (")
                        f(stmnts, indent + "    ")
                        text.append(f"{indent}))")
                    case ("else", stmnts):
                        text.append(f"{indent}('else', (")
                        f(stmnts, indent + "    ")
                        text.append(f"{indent}))")
                    case _:
                        text.append(f"{indent}{c}")

        f(self._code)
        return "\n".join(text)

    @contextmanager
    def if_stmt(self, expr: _IntExpr):
        code = self._code
        self._code = []
        try:
            yield None
        finally:
            code.append(("when", _logic_value(expr).expr, tuple(self._code)))
            self._code = code

    @contextmanager
    def elif_stmt(self, expr: _IntExpr):
        assert self._code[-1][0] in ("when", "else-when")
        code = self._code
        self._code = []
        try:
            yield None
        finally:
            code.append(
                ("else-when", _logic_value(expr).expr, tuple(self._code))
            )
            self._code = code

    @contextmanager
    def else_stmt(self):
        assert self._code[-1][0] in ("when", "else-when")
        code = self._code
        self._code = []
        try:
            yield None
        finally:
            code.append(("else", tuple(self._code)))
            self._code = code

    def and_expr(self, *ops):
        ops2 = [_logic_value(x) for x in ops]
        return _reduce2(_AndExpr, *ops2)

    def or_expr(self, *ops):
        ops2 = [_logic_value(x) for x in ops]
        return _reduce2(_OrExpr, *ops2)

    def not_expr(self, op):
        return _NotExpr(_logic_value(op))
