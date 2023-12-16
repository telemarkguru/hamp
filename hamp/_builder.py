"""Code builder"""

from contextlib import contextmanager
from typing import Union, Tuple, List, Any
from . import _module
from ._hwtypes import _Struct, _Int, _SInt, _Array, u1
from ._struct import member


ExprType = Union[str, int, "_VarBuilder"]
ExprRType = Union[str, int, tuple["ExprRType", ...]]


class _VarBuilder:
    """Represents"""

    _VARS = set(("builder", "item", "name"))

    def __init__(self, builder: "_CodeBuilder", name: ExprRType, item):
        self.builder = builder
        self.name = name
        self.item = item

    def _expr(self, e: ExprRType, item=None) -> "_VarBuilder":
        return _VarBuilder(self.builder, e, item or self.item)

    def __setattr__(self, name, value):
        value = _value_str(value)
        if name in _VarBuilder._VARS:
            super().__setattr__(name, value)
            return
        self.builder.code.append(("connect", (".", self.name, name), value))

    def __getattr__(self, name: str) -> "_VarBuilder":
        if isinstance(self.item, _Struct):
            item = member(self.item, name)
        elif hasattr(self.item, name):
            item = getattr(self.item, name)
        else:
            raise AttributeError(f"{self.name} has no member {name}")
        return self._expr((".", self.name, name), item)

    def _chk_slice(self, slice):
        if not isinstance(self.item, _Int):
            raise TypeError(f"{self.name} is not a bit-vector")
        error = None
        if not (isinstance(slice.start, int) and isinstance(slice.stop, int)):
            error = "Slice indexes must be integer constants"
        elif slice.step is not None:
            error = "Step in slice index not allowed"
        elif slice.stop > slice.start:
            error = "Slice MSB must be equal to or larger than LSB"
        if error:
            slicestr = str(slice)[6:-1].replace(", ", ":")
            raise IndexError(f"{error}: {self.name}[{slicestr}]")

    def _chk_idx(self, idx):
        if not isinstance(self.item, _Array):
            raise TypeError(f"{self.name} is not an array")
        if isinstance(idx, int):
            size = self.item.size
            if not 0 <= idx < size:
                raise IndexError(
                    f"{self.name}[{idx}] is out of range (size={size})"
                )
            return idx
        return _value_str(idx)

    def __getitem__(self, idx) -> "_VarBuilder":
        if isinstance(idx, slice):
            self._chk_slice(idx)
            return self._expr(("bits", self.name, idx.start, idx.stop))
        elif isinstance(self.item, _Int):
            return self[idx:idx]
        idx = self._chk_idx(idx)
        return self._expr(("[]", self.name, _value_str(idx)))

    def __setitem__(self, idx, value) -> None:
        idx = self._chk_idx(idx)
        v1 = _value_str(value)
        self.builder.code.append(("connect", ("[]", self.name, idx), v1))

    def _op2(self, op: str, value: ExprType, item=None) -> "_VarBuilder":
        v1 = _value_str(self)
        v2 = _value_str(value)
        return self._expr((op, v1, v2), item)

    def _rop2(self, op: str, value: ExprType) -> "_VarBuilder":
        v1 = _value_str(value)
        v2 = _value_str(self)
        return self._expr((op, v1, v2))

    def _op1(self, op: str) -> "_VarBuilder":
        v1 = _value_str(self)
        return self._expr((op, v1))

    def __add__(self, value: ExprType) -> "_VarBuilder":
        return self._op2("+", value)

    def __radd__(self, value: ExprType) -> "_VarBuilder":
        return self._rop2("+", value)

    def __sub__(self, value: ExprType) -> "_VarBuilder":
        return self._op2("-", value)

    def __rsub__(self, value: ExprType) -> "_VarBuilder":
        return self._rop2("-", value)

    def __mul__(self, value: ExprType) -> "_VarBuilder":
        return self._op2("*", value)

    def __rmul__(self, value: ExprType) -> "_VarBuilder":
        return self._rop2("*", value)

    def __mod__(self, value: ExprType) -> "_VarBuilder":
        return self._op2("%", value)

    def __floordiv__(self, value: ExprType) -> "_VarBuilder":
        return self._op2("//", value)

    def __rfloordiv__(self, value: ExprType) -> "_VarBuilder":
        return self._rop2("//", value)

    def __or__(self, value: ExprType) -> "_VarBuilder":
        return self._op2("|", value)

    def __ror__(self, value: ExprType) -> "_VarBuilder":
        return self._rop2("|", value)

    def __and__(self, value: ExprType) -> "_VarBuilder":
        return self._op2("&", value)

    def __rand__(self, value: ExprType) -> "_VarBuilder":
        return self._rop2("&", value)

    def __xor__(self, value: ExprType) -> "_VarBuilder":
        return self._op2("^", value)

    def __rxor__(self, value: ExprType) -> "_VarBuilder":
        return self._rop2("^", value)

    def __lshift__(self, value: ExprType) -> "_VarBuilder":
        return self._op2("<<", value)

    def __rlshift__(self, value: ExprType) -> "_VarBuilder":
        return self._rop2("<<", value)

    def __rshift__(self, value: ExprType) -> "_VarBuilder":
        return self._op2(">>", value)

    def __rrshift__(self, value: ExprType) -> "_VarBuilder":
        return self._rop2(">>", value)

    def __neg__(self) -> "_VarBuilder":
        return self._op1("neg")

    def __pos__(self) -> "_VarBuilder":
        return self._op1("pos")

    def __eq__(self, value: ExprType) -> "_VarBuilder":  # type: ignore[override]
        return self._op2("==", value, u1)

    def __ge__(self, value: ExprType) -> "_VarBuilder":  # type: ignore[override]
        return self._op2(">=", value, u1)

    def __gt__(self, value: ExprType) -> "_VarBuilder":  # type: ignore[override]
        return self._op2(">", value, u1)

    def __le__(self, value: ExprType) -> "_VarBuilder":  # type: ignore[override]
        return self._op2("<=", value, u1)

    def __lt__(self, value: ExprType) -> "_VarBuilder":  # type: ignore[override]
        return self._op2("<", value, u1)

    def __ne__(self, value: ExprType) -> "_VarBuilder":  # type: ignore[override]
        return self._op2("!=", value, u1)


def _value_str(value: ExprType) -> ExprRType:
    if isinstance(value, _VarBuilder):
        return value.name
    return value


def _logic_str(value: ExprType) -> ExprRType:
    if isinstance(value, _VarBuilder):
        item = value.item
        if (
            isinstance(item, _Int)
            and item.size != 1
            or isinstance(item, _SInt)
        ):
            return ("orr", value.name)
        return value.name
    return value


# CodeListItemType = Tuple[str, Unpack[Tuple[ExprRType, ...]]]
CodeListItemType = Tuple[Any, ...]


class _CodeBuilder:
    """Represents a module when generating code"""

    _VARS = set(("module", "code"))

    def __init__(self, module: _module._Module):
        self.module = module
        self.code: List[CodeListItemType] = []

    def __setattr__(self, name: str, value) -> None:
        """Assign value"""
        if name in _CodeBuilder._VARS:
            super().__setattr__(name, value)
            return
        assert name in self.module
        item = self.module[name]
        assert isinstance(item, _module._DataMember)
        # TODO: check that member is output or wire
        self.code.append(("connect", name, _value_str(value)))

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

    def __getattr__(
        self, name: str
    ) -> Union[_VarBuilder, _module._ModuleMember, bool]:
        assert name in self.module
        item = self.module[name]
        if isinstance(item, _module._DataMember):
            return _VarBuilder(self, name, item.type)
        if isinstance(item, _module._ModuleFunc):
            return self.module[name]
        assert False

    @contextmanager
    def if_stmt(self, expr):
        self.code.append(("when", _logic_str(expr)))
        try:
            yield None
        finally:
            self.code.append(("end_when",))

    @contextmanager
    def elif_stmt(self, expr):
        assert self.code[-1] == ("end_when",)
        self.code[-1] = ("else_when", _logic_str(expr))
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

    def _reduce_op(self, name, *ops):
        if len(ops) == 2:
            return (name, _logic_str(ops[0]), _logic_str(ops[1]))
        op, *rops = ops
        return (name, _logic_str(op), self._reduce_op(name, *rops))

    def and_expr(self, *ops):
        return self._reduce_op("and", *ops)

    def or_expr(self, *ops):
        return self._reduce_op("or", *ops)

    def not_expr(self, op):
        return ("not", _logic_str(op))
