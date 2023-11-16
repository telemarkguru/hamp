"""Code builder"""

from contextlib import contextmanager
from typing import Union, Tuple, List, Any
from . import _module
from . import _hwtypes
from ._struct import member


ExprType = Union[str, int, "_VarBuilder", Tuple["ExprType", ...]]
ExprRType = Union[str, int, tuple["ExprType", ...]]


class _VarBuilder:
    """Represents"""

    _VARS = set(("builder", "item", "name"))

    def __init__(self, builder: "_CodeBuilder", name: str, item):
        self.builder = builder
        self.name = name
        self.item = item

    def __setattr__(self, name, value):
        value = _value_str(value)
        if name in _VarBuilder._VARS:
            super().__setattr__(name, value)
            return
        self.builder.code.append(("connect", f"{self.name}.{name}", value))

    def __getattr__(self, name) -> "_VarBuilder":
        if m := member(self.item, name):
            item = m
        elif hasattr(self.item, name):
            item = getattr(self.item, name)
        else:
            raise AttributeError(f"{self.name} has no member {name}")
        return _VarBuilder(self.builder, f"{self.name}.{name}", item)

    def _chk_slice(self, slice):
        if not isinstance(self.item, _hwtypes._Int):
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
        if not isinstance(self.item, _hwtypes._Array):
            raise TypeError(f"{self.name} is not an array")
        if isinstance(idx, int):
            size = self.item.size
            if not 0 <= idx < size:
                raise IndexError(
                    f"{self.name}[{idx}] is out of range (size={size})"
                )
            idx = str(idx)
        return _value_str(idx)

    def __getitem__(self, idx) -> Union["_VarBuilder", ExprRType]:
        if isinstance(idx, slice):
            self._chk_slice(idx)
            return ("bits", self.name, idx.start, idx.stop)
        idx = self._chk_idx(idx)
        return _VarBuilder(self.builder, f"{self.name}[{idx}]", self.item.type)

    def __setitem__(self, idx, value):
        idx = self._chk_idx(idx)
        value = _value_str(value)
        self.builder.code.append(("connect", f"{self.name}[{idx}]", value))

    def _op2(self, op: str, value: ExprType) -> ExprRType:
        value = _value_str(value)
        return (op, self.name, value)

    def _rop2(self, op: str, value: ExprType) -> ExprRType:
        value = _value_str(value)
        return (op, value, self.name)

    def _op1(self, op: str) -> ExprRType:
        return (op, self.name)

    def __add__(self, value: ExprType) -> ExprRType:
        return self._op2("+", value)

    def __radd__(self, value: ExprType) -> ExprRType:
        return self._rop2("+", value)

    def __sub__(self, value: ExprType) -> ExprRType:
        return self._op2("-", value)

    def __rsub__(self, value: ExprType) -> ExprRType:
        return self._rop2("-", value)

    def __mul__(self, value: ExprType) -> ExprRType:
        return self._op2("*", value)

    def __rmul__(self, value: ExprType) -> ExprRType:
        return self._rop2("*", value)

    def __mod__(self, value: ExprType) -> ExprRType:
        return self._op2("%", value)

    def __rmod__(self, value: ExprType) -> ExprRType:
        return self._rop2("%", value)

    def __or__(self, value: ExprType) -> ExprRType:
        return self._op2("|", value)

    def __ror__(self, value: ExprType) -> ExprRType:
        return self._rop2("|", value)

    def __and__(self, value: ExprType) -> ExprRType:
        return self._op2("&", value)

    def __rand__(self, value: ExprType) -> ExprRType:
        return self._rop2("&", value)

    def __xor__(self, value: ExprType) -> ExprRType:
        return self._op2("^", value)

    def __rxor__(self, value: ExprType) -> ExprRType:
        return self._rop2("^", value)

    def __lshift__(self, value: ExprType) -> ExprRType:
        return self._op2("<<", value)

    def __rlshift__(self, value: ExprType) -> ExprRType:
        return self._rop2("<<", value)

    def __rshift__(self, value: ExprType) -> ExprRType:
        return self._op2(">>", value)

    def __rrshift__(self, value: ExprType) -> ExprRType:
        return self._rop2(">>", value)

    def __neg__(self) -> ExprRType:
        return self._op1("neg")

    def __pos__(self) -> ExprRType:
        return self._op1("pos")

    def __eq__(self, value: ExprType) -> ExprRType:  # type: ignore[override]
        return self._op2("==", value)

    def __ge__(self, value: ExprType) -> ExprRType:  # type: ignore[override]
        return self._op2(">=", value)

    def __gt__(self, value: ExprType) -> ExprRType:  # type: ignore[override]
        return self._op2(">", value)

    def __le__(self, value: ExprType) -> ExprRType:  # type: ignore[override]
        return self._op2("<=", value)

    def __lt__(self, value: ExprType) -> ExprRType:  # type: ignore[override]
        return self._op2("<", value)

    def __ne__(self, value: ExprType) -> ExprRType:  # type: ignore[override]
        return self._op2("!=", value)


def _value_str(value: ExprType) -> ExprRType:
    if isinstance(value, _VarBuilder):
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

    def __getattr__(self, name: str) -> _VarBuilder:
        assert name in self.module
        item = self.module[name]
        if isinstance(item, _module._DataMember):
            return _VarBuilder(self, name, item.type)
        if isinstance(item, _module._ModuleFunc):
            return self.module[name]
        assert False

    @contextmanager
    def if_stmt(self, expr):
        self.code.append(("when", _value_str(expr)))
        try:
            yield None
        finally:
            self.code.append(("end_when",))

    @contextmanager
    def elif_stmt(self, expr):
        assert self.code[-1] == ("end_when",)
        self.code[-1] = ("else_when", _value_str(expr))
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
        return ("and", *ops)

    def or_expr(self, *ops):
        return ("or", *ops)

    def not_expr(self, op):
        return ("not", op)
