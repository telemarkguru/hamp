"""Code builder"""

from contextlib import contextmanager
from typing import Union, Tuple, List, Unpack


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
        assert name in self.item
        return _VarBuilder(
            self.builder, f"{self.name}.{name}", getattr(self.item, name)
        )

    def __getitem__(self, idx) -> "_VarBuilder":
        return _VarBuilder(
            self.builder, f"{self.name}[idx]", self.item[idx]
        )

    def __setitem__(self, idx, value):
        value = _value_str(value)
        self.buidler.code.append(("connect", f"{self.name}[{idx}]", value))

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
    if isinstance(value, int):
        if value >= 0:
            return f"uint({value})"
        else:
            return f"sint({value})"
    return value


CodeListItemType = Tuple[str, Unpack[Tuple[ExprRType, ...]]]


class _CodeBuilder:
    """Represents a module when generating code"""

    _VARS = set(("module", "code"))

    def __init__(self, module) -> None:
        self.module = module
        self.code: List[CodeListItemType] = []

    def __setattr__(self, name, value):
        """Assign value"""
        if name in _CodeBuilder._VARS:
            super().__setattr__(name, value)
            return
        assert name in self.module
        # TODO: check that member is output or wire
        self.code.append(("connect", name, value))

    def __str__(self) -> str:
        text = []
        indent = 0

        def pr(x):
            text.append(f"{' ' * (indent*4)}{x}")

        for c in self.code:
            if c[0] == "end_when":
                indent -= 1
                pr(c)
            elif c[0] == "when":
                pr(c)
                indent += 1
            elif c[0] in ("else_when", "else"):
                indent -= 1
                pr(c)
                indent += 1
            else:
                pr(c)
        return "\n".join(text)

    def __getattr__(self, name):
        assert name in self.module
        return _VarBuilder(self, name, getattr(self.module, name))

    @contextmanager
    def if_stmt(self, expr):
        self.code.append(("when", expr))
        try:
            yield None
        finally:
            self.code.append(("end_when",))

    @contextmanager
    def elif_stmt(self, expr):
        assert self.code[-1] == ("end_when",)
        self.code[-1] = ("else_when", expr)
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
