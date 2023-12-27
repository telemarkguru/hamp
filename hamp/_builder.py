"""Code builder"""

from contextlib import contextmanager
from typing import Union, Tuple, List, Any
from . import _module
from ._hwtypes import _Struct, _Int, _SInt, _Array, u1, uint, _IntValue
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
        if name in _VarBuilder._VARS:
            super().__setattr__(name, value)
            return
        value, item = _value_str(value)
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
            return idx, 0
        return _value_str(idx)

    def __getitem__(self, idx) -> "_VarBuilder":
        if isinstance(idx, slice):
            self._chk_slice(idx)
            size = idx.start - idx.stop + 1
            return self._expr(
                ("bits", self.name, idx.start, idx.stop), uint[size]
            )
        elif isinstance(self.item, _Int):
            return self[idx:idx]
        idx, item = self._chk_idx(idx)
        # TODO: check type
        return self._expr(("[]", self.name, idx), self.item.type)

    def __setitem__(self, idx, value) -> None:
        idx, idxitem = self._chk_idx(idx)
        v1, item = _value_str(value)
        self.builder.code.append(("connect", ("[]", self.name, idx), v1))

    def _op2(self, op: str, value: ExprType, item=None) -> "_VarBuilder":
        v1, i1 = _value_str(self)
        v2, i2 = _value_str(value)
        return self._expr((op, v1, v2), item)

    def _rop2(self, op: str, value: ExprType) -> "_VarBuilder":
        v1, i1 = _value_str(value)
        v2, i2 = _value_str(self)
        return self._expr((op, v1, v2))

    def _op1(self, op: str) -> "_VarBuilder":
        v1, i1 = _value_str(self)
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
        return value.name, value.item
    if isinstance(value, _IntValue):
        return value, value.type
    if not isinstance(value, int):
        raise TypeError(f"Expected integer, got '{value}'")
    return value, value.bit_length()


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

    _VARS = set(("module", "code", "cat"))

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
        # TODO: check that member is (part of) output, wire or register
        v1, it = _value_str(value)
        self.code.append(("connect", name, v1))

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

    def _reduce_logic_op(self, name, *ops):
        assert len(ops) >= 2
        if len(ops) == 2:
            return _VarBuilder(
                self, (name, _logic_str(ops[0]), _logic_str(ops[1])), u1
            )
        op, *rops = ops
        op2 = self._reduce_logic_op(name, *rops)
        return _VarBuilder(self, (name, _logic_str(op), op2.name), u1)

    def and_expr(self, *ops):
        return self._reduce_logic_op("and", *ops)

    def or_expr(self, *ops):
        return self._reduce_logic_op("or", *ops)

    def not_expr(self, op):
        return _VarBuilder(self, ("not", _logic_str(op)), u1)

    def _reduce_op(self, name, typecheck, *ops):
        assert len(ops) >= 2
        if len(ops) == 2:
            v1, i1 = _value_str(ops[0])
            v2, i2 = _value_str(ops[1])
            t = typecheck(i1, i2)
            return _VarBuilder(self, (name, v1, v2), t)
        op, *rops = ops
        v1, i1 = _value_str(op)
        op2 = self._reduce_op(name, *rops)
        i2 = op2.item
        t = typecheck(i1, i2)
        return _VarBuilder(self, (name, v1, op2.name), t)

    def _cat_typecheck(self, t1, t2):
        assert isinstance(t1, _Int)
        assert isinstance(t2, _Int)
        return uint[t1.size + t2.size]

    def cat(self, *ops):
        return self._reduce_op("cat", self._cat_typecheck, *ops)
