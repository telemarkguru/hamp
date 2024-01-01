"""Code builder"""

from contextlib import contextmanager
from typing import Union, Tuple, List, Any, Type
from . import _module
from ._hwtypes import (
    _Struct,
    _Int,
    _SInt,
    _Array,
    u1,
    uint,
    sint,
    _IntValue,
    equivalent,
)
from ._struct import member


ExprType = Union[str, int, "_Var"]
ExprRType = Union[str, int, tuple["ExprRType", ...]]

OpType = Union["_Expr", int]


class _Expr:
    """Ingeger Expression"""

    type: _Int

    def __init__(self, type: _Int):
        self.type = type

    @property
    def size(self) -> int:
        return self.type.size

    def new_type(self, size) -> _Int:
        if isinstance(self.type, _SInt):
            return sint[size]
        else:
            return uint[size]

    def expr(self):
        assert False

    def _chk_slice(self, slice):
        error = None
        if not (isinstance(slice.start, int) and isinstance(slice.stop, int)):
            error = "Slice indexes must be integer constants"
        elif slice.step is not None:
            error = "Step in slice index not allowed"
        elif slice.stop > slice.start:
            error = "Slice MSB must be equal to or larger than LSB"
        if error:
            slicestr = str(slice)[6:-1].replace(", ", ":")
            raise IndexError(f"{error}: {self._name}[{slicestr}]")

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
        return _LShiftExpr(self, value)

    def __rlshift__(self, value: OpType) -> "_Expr":
        return _LShiftExpr(value, self)

    def __rshift__(self, value: OpType) -> "_Expr":
        return _RShiftExpr(self, value)

    def __rrshift__(self, value: OpType) -> "_Expr":
        return _RShiftExpr(value, self)

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


class _ConstExpr(_Expr):
    value: _IntValue

    def __init__(self, value, signed, size=None):
        type = sint if signed else uint
        if size:
            type = type[size]
        else:
            type = type.unsized
        super().__init__(type)
        self.value = type(value)

    @property
    def size(self):
        if (s := self.value.type.size) == -1:
            return self.value.value.bit_length()
        return s

    def expr(self):
        t = self.value.type
        return (t.type, t.size, self.value.value)


def _infer_int(type, value) -> _Expr:
    if not isinstance(type, _Int):
        raise TypeError(f"Cannot infer integer for type {type}")
    return _ConstExpr(value, type.signed, type.size)


class _BitsExpr(_Expr):
    op = "bits"
    v1: _Expr
    start: int
    stop: int
    size: int

    def __init__(self, v1: _Expr, start: int, stop: int, size: int):
        self.type = uint[size]
        self.start = start
        self.stop = stop
        self.v1 = v1

    def expr(self):
        return (self.op, self.v1.expr(), self.start, self.stop)


class _TwoOpExpr(_Expr):
    op: str
    v1: _Expr
    v2: _Expr

    def __init__(self, v1: OpType, v2: OpType):
        assert isinstance(v1, (int, _Expr))
        assert isinstance(v2, (int, _Expr))
        if isinstance(v1, _Expr):
            s1 = v1.type.signed
            self.v1 = v1
        if isinstance(v2, _Expr):
            s2 = v2.type.signed
            self.v2 = v2
        if isinstance(v1, int):
            self.v1 = _ConstExpr(v1, s2)
        elif isinstance(v2, int):
            self.v2 = _ConstExpr(v2, s1)
        self.check_types()
        super().__init__(self.infer_type())

    def expr(self):
        return (self.op, self.v1.expr(), self.v2.expr())

    def check_types(self):
        if self.v1.type.signed != self.v2.type.signed:
            raise TypeError(
                "Both operands must have same sign "
                f"{self.op}: {self.v1.type} {self.v2.type}"
            )

    def infer_type(self):
        assert False


class _CatExpr(_TwoOpExpr):
    op = "cat"

    def infer_type(self) -> _Int:
        size = self.v1.size + self.v2.size
        return uint[size]


class _AddExpr(_TwoOpExpr):
    op = "+"

    def infer_type(self) -> _Int:
        size = max(self.v1.size, self.v2.size) + 1
        return self.v1.new_type(size)


class _SubExpr(_TwoOpExpr):
    op = "-"

    def infer_type(self) -> _Int:
        size = max(self.v1.size, self.v2.size) + 1
        return self.v1.new_type(size)


class _MulExpr(_TwoOpExpr):
    op = "*"

    def infer_type(self) -> _Int:
        size = self.v1.size + self.v2.size
        return self.v1.new_type(size)


class _ModExpr(_TwoOpExpr):
    op = "%"

    def infer_type(self) -> _Int:
        size = min(self.v1.size, self.v2.size)
        return self.v1.new_type(size)


class _DivExpr(_TwoOpExpr):
    op = "//"

    def infer_type(self) -> _Int:
        size = self.v1.size + self.v1.type.signed
        return self.v1.new_type(size)


class _OrExpr(_TwoOpExpr):
    op = "|"

    def infer_type(self) -> _Int:
        size = max(self.v1.size, self.v2.size)
        return uint[size]


class _AndExpr(_TwoOpExpr):
    op = "&"

    def infer_type(self) -> _Int:
        size = max(self.v1.size, self.v2.size)
        return uint[size]


class _XorExpr(_TwoOpExpr):
    op = "^"

    def infer_type(self) -> _Int:
        size = max(self.v1.size, self.v2.size)
        return uint[size]


class _LShiftExpr(_TwoOpExpr):
    op = "<<"

    def check_types(self):
        if self.v2.type.signed:
            raise TypeError(
                "Shift amount must be an unsigned value"
                f"{self.op}: {self.v1.type} {self.v2.type}"
            )

    def infer_type(self) -> _Int:
        if isinstance(self.v2, _ConstExpr):
            size = self.v1.size + self.v2.value.value
        else:
            size = self.v1.size + 2**self.v1.size - 1
        return self.v1.new_type(size)


class _RShiftExpr(_TwoOpExpr):
    op = ">>"

    def check_types(self):
        if self.v2.type.signed:
            raise TypeError(
                "Shift amount must be an unsigned value"
                f"{self.op}: {self.v1.type} {self.v2.type}"
            )

    def infer_type(self) -> _Int:
        if isinstance(self.v2, _ConstExpr):
            size = max(self.v1.size - self.v2.value.value, 1)
        else:
            size = self.v1.size
        return self.v1.new_type(size)


class _EqExpr(_TwoOpExpr):
    op = "=="

    def infer_type(self) -> _Int:
        return u1


class _GeExpr(_TwoOpExpr):
    op = ">="

    def infer_type(self) -> _Int:
        return u1


class _GtExpr(_TwoOpExpr):
    op = ">"

    def infer_type(self) -> _Int:
        return u1


class _LeExpr(_TwoOpExpr):
    op = "<="

    def infer_type(self) -> _Int:
        return u1


class _LtExpr(_TwoOpExpr):
    op = "<"

    def infer_type(self) -> _Int:
        return u1


class _NeExpr(_TwoOpExpr):
    op = "!="

    def infer_type(self) -> _Int:
        return u1


def _reduce2(cls: Type[_TwoOpExpr], *ops: OpType) -> _Expr:
    assert len(ops) >= 2
    if len(ops) == 2:
        return cls(ops[0], ops[1])
    return cls(ops[0], _reduce2(cls, *ops[1:]))


class _OneOpExpr(_Expr):
    op: str

    def __init__(self, v1: OpType):
        assert isinstance(v1, _Expr)
        self.v1 = v1
        t = self.infer_type()
        super().__init__(t)

    def infer_type(self) -> _Int:
        return self.v1.type

    def expr(self):
        return (self.op, self.v1.expr())


class _CvtExpr(_OneOpExpr):
    op = "cvt"

    def infer_type(self) -> _Int:
        if self.v1.type.signed:
            return self.v1.type
        return sint[self.v1.size + 1]


class _NegExpr(_OneOpExpr):
    op = "neg"

    def infer_type(self) -> _Int:
        return sint[self.v1.size + 1]


class _NotExpr(_OneOpExpr):
    op = "not"

    def infer_type(self) -> _Int:
        return uint[self.v1.size]


class _OrrExpr(_OneOpExpr):
    op = "orr"

    def infer_type(self) -> _Int:
        return u1


class _Var:
    _name: str
    _builder: "_CodeBuilder"
    _base: Union["_Var", None]

    def __init__(
        self,
        name: str,
        builder: "_CodeBuilder",
        base: Union["_Var", None] = None,
    ):
        self._name = name
        self._builder = builder
        self._base = base


class _IntVarExpr(_Expr, _Var):
    def __init__(
        self,
        type: _Int,
        name: str,
        builder: "_CodeBuilder",
        base: Union[_Var, None] = None,
    ):
        _Expr.__init__(self, type)
        _Var.__init__(self, name, builder, base)

    def expr(self, _=None):
        if self._base:
            return self._base.expr(self._name)
        return self._name


class _StructVar(_Var):
    _VARS = set(("_name", "type", "_builder", "_base"))
    type: _Struct

    def __init__(
        self,
        type: _Struct,
        name: str,
        builder: "_CodeBuilder",
        base: Union[_Var, None] = None,
    ):
        super().__init__(name, builder, base)
        self.type = type

    def __getattr__(self, name: str) -> _Var:
        item = member(self.type, name)
        return _vartype(item, name, self._builder, self)

    def __setattr__(self, name: str, value: Union[_Expr, int]):
        if name in _StructVar._VARS:
            super().__setattr__(name, value)
            return
        item = member(self.type, name)
        if isinstance(value, int):
            value = _infer_int(item, value)
        if not equivalent(value.type, item, False):
            raise TypeError(
                f"Cannot assign non-equivalent type {value.type} to {type}"
            )
        self._builder.code.append(("connect", self.expr(name), value.expr()))

    def expr(self, name=""):
        if not name:
            if self._base:
                return self._base.expr(self._name)
            return self._name
        if self._base:
            return (".", self._base.expr(self._name), name)
        return (".", self._name, name)


class _ArrayVar(_Var):
    type: _Array
    idx: Union[_Expr, None]

    def __init__(
        self,
        type: _Array,
        name: str,
        builder: "_CodeBuilder",
        base: Union[_Var, None] = None,
    ):
        super().__init__(name, builder, base)
        self.type = type
        self.idx = None

    def _chk_idx(self, idx: int) -> _ConstExpr:
        size = self.type.size
        if not 0 <= idx < size:
            raise IndexError(
                f"{self._name}[{idx}] is out of range (size={size})"
            )
        return _ConstExpr(idx, False)

    def __getitem__(self, idx: OpType) -> _Var:
        if isinstance(idx, slice):
            raise TypeError(f"{self._name} is not a bit-vector")
        if isinstance(idx, int):
            idx = self._chk_idx(idx)
        self.idx = idx
        return _vartype(self.type.type, "", self._builder, self)

    def __setitem__(self, idx: OpType, value: OpType) -> None:
        type = self.type.type
        if isinstance(idx, int):
            idx = self._chk_idx(idx)
        self.idx = idx
        if isinstance(value, int):
            value = _ConstExpr(value, type.signed)
        if not equivalent(value.type, type, False):
            raise TypeError(
                f"Cannot assign non-equivalent type {value.type} to {type}"
            )
        self._builder.code.append(("connect", self.expr(""), value.expr()))

    def expr(self, _=None):
        if self._base:
            if self.idx is None:
                return self._base.expr(self._name)
            else:
                return ("[]", self._base.expr(self._name), self.idx.expr())
        else:
            if self.idx is None:
                return self._name
            else:
                return ("[]", self._name, self.idx.expr())


class _InstanceVar(_Var):
    _VARS = set(("_name", "type", "_builder", "_base"))
    type: _module._Module

    def __init__(
        self,
        type: _module._Module,
        name: str,
        builder: "_CodeBuilder",
        base: Union[_Var, None] = None,
    ):
        super().__init__(name, builder, base)
        self.type = type

    def __getattr__(self, name: str) -> _Var:
        if name not in self.type:
            raise AttributeError(
                f"Module {self.type.name} has no member {name}"
            )
        item = self.type[name]
        if isinstance(item, _module._DataMember):
            return _vartype(item.type, name, self._builder, self)
        raise TypeError(
            f"Cannot access {name} in instance of {self.type.type.name}"
        )

    def __setattr__(self, name: str, value: Union[_Expr, int]):
        if name in _InstanceVar._VARS:
            super().__setattr__(name, value)
            return
        if name not in self.type:
            raise AttributeError(
                f"Module {self.type.name} has no member {name}"
            )
        item = self.type[name]
        assert isinstance(item, _module._DataMember)
        # TODO: check that member is (part of) output, wire or register
        if isinstance(value, int):
            value = _infer_int(item.type, value)
        if not equivalent(value.type, item.type, False):
            raise TypeError(
                f"Cannot assign non-equivalent type {value.type} to {item.type}"
            )
        self._builder.code.append(("connect", self.expr(name), value.expr()))

    def expr(self, name):
        return (".", self._name, name)


def _vartype(type, name, builder, base) -> _Var:
    if isinstance(type, _Struct):
        return _StructVar(type, name, builder, base)
    elif isinstance(type, _Array):
        return _ArrayVar(type, name, builder, base)
    elif isinstance(type, _module._Module):
        return _InstanceVar(type, name, builder, base)
    return _IntVarExpr(type, name, builder, base)


def _logic_value(value: OpType) -> OpType:
    if isinstance(value, _Expr):
        type = value.type
        if (
            isinstance(type, _Int)
            and type.size != 1
            or isinstance(type, _SInt)
        ):
            return _OrrExpr(value)
        return value
    return _ConstExpr(int(bool(value)), False, 1)


# CodeListItemType = Tuple[str, Unpack[Tuple[ExprRType, ...]]]
CodeListItemType = Tuple[Any, ...]


class _CodeBuilder:
    """Represents a module when generating code"""

    _VARS = set(("module", "code", "cat"))

    def __init__(self, module: _module._Module):
        self.module = module
        self.code: List[CodeListItemType] = []

    def __getattr__(
        self, name: str
    ) -> Union[_Var, _module._ModuleMember, bool]:
        if name not in self.module:
            raise AttributeError(
                f"Module {self.module.name} has no member {name}"
            )
        item = self.module[name]
        if isinstance(item, _module._ModuleFunc):
            return self.module[name]
        if isinstance(item, _module._DataMember):
            return _vartype(item.type, name, self, None)
        return False

    def __setattr__(self, name: str, value) -> None:
        """Assign value"""
        if name in _CodeBuilder._VARS:
            super().__setattr__(name, value)
            return
        if name not in self.module:
            raise AttributeError(
                f"Module {self.module.name} has no member {name}"
            )
        item = self.module[name]
        assert isinstance(item, _module._DataMember)
        # TODO: check that member is (part of) output, wire or register
        if isinstance(value, int):
            value = _infer_int(item.type, value)
        if not equivalent(value.type, item.type, False):
            raise TypeError(
                f"Cannot assign non-equivalent type {value.type} to {item.type}"
            )
        self.code.append(("connect", name, value.expr()))

    def iter_with_indent(self):
        indent = 0

        for c in self.code:
            if c[0] == "end_when":
                indent -= 1
                yield c, indent
            elif c[0] == "when":
                yield c, indent
                indent += 1
            elif c[0] in ("else_when", "else"):
                indent -= 1
                yield c, indent
                indent += 1
            else:
                yield c, indent

    def __str__(self) -> str:
        text = []
        for c, indent in self.iter_with_indent():
            text.append(f"{' ' * (indent*4)}{c}")
        return "\n".join(text)

    @contextmanager
    def if_stmt(self, expr):
        self.code.append(("when", _logic_value(expr).expr()))
        try:
            yield None
        finally:
            self.code.append(("end_when",))

    @contextmanager
    def elif_stmt(self, expr):
        assert self.code[-1] == ("end_when",)
        self.code[-1] = ("else_when", _logic_value(expr).expr())
        try:
            yield None
        finally:
            self.code.append(("end_when",))

    @contextmanager
    def else_stmt(self):
        assert self.code[-1] == ("end_when",)
        self.code[-1] = ("else",)
        try:
            yield None
        finally:
            self.code.append(("end_when",))

    def and_expr(self, *ops):
        ops2 = [_logic_value(x) for x in ops]
        print("ops2", [(x.expr(), x.type) for x in ops2])
        return _reduce2(_AndExpr, *ops2)

    def or_expr(self, *ops):
        ops2 = [_logic_value(x) for x in ops]
        return _reduce2(_OrExpr, *ops2)

    def not_expr(self, op):
        return _NotExpr(_logic_value(op))

    def cat(self, *ops):
        return _reduce2(_CatExpr, *ops)
