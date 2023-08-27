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
        if name in _VarBuilder._VARS:
            super().__setattr__(name, value)
            return
        self.builder.code.append(("connect", f"{self.name}.{name}", value))

    def __getattr__(self, name):
        assert name in self.item
        return _VarBuilder(
            self.builder, f"{self.name}.{name}", getattr(self.item, name)
        )

    def _op2(self, op: str, value: ExprType) -> ExprRType:
        if isinstance(value, _VarBuilder):
            value = value.name
        elif isinstance(value, int):
            if value >= 0:
                value = f"uint({value})"
            else:
                value = f"sint({value})"
        return (op, self.name, value)

    def __add__(self, value: ExprType) -> ExprRType:
        return self._op2("+", value)

    def __eq__(self, value: ExprType) -> ExprRType:  # type: ignore[override]
        return self._op2("==", value)

    def __gt__(self, value: ExprType) -> ExprRType:  # type: ignore[override]
        return self._op2(">", value)


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
