"""Code builder"""

from contextlib import contextmanager
from typing import Union, Tuple, List, Any, Type, Sequence
from ._module import (
    _Module,
    _ModuleMember,
    _DataMember,
    _ModuleCode,
    _ModuleFunc,
    _Instance,
    _Port,
    _Wire,
    _Register,
)

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
    INPUT,
    OUTPUT,
)
from ._struct import member
from ._convert import convert


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

    def expr(self):  # pragma: no cover
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
        return (t.expr(), self.value.value)


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
        return (
            self.type.expr(),
            (self.op, self.v1.expr(), self.start, self.stop),
        )


class _TwoOpExpr(_Expr):
    op: str
    v1: _Expr
    v2: _Expr

    def __init__(self, v1: OpType, v2: OpType, v2signed=None):
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
            if v2signed is not None:
                s1 = v2signed
            self.v2 = _ConstExpr(v2, s1)
        self.check_types()
        super().__init__(self.infer_type())

    def expr(self):
        return (self.type.expr(), (self.op, self.v1.expr(), self.v2.expr()))

    def check_types(self):
        if self.v1.type.signed != self.v2.type.signed:
            raise TypeError(
                "Both operands must have same sign "
                f"{self.op}: {self.v1.type} {self.v2.type}"
            )

    def infer_type(self):  # pragma: no cover
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

    def infer_type(self) -> _Int:  # pragma: no cover
        assert False

    def expr(self):
        return (self.type.expr(), (self.op, self.v1.expr()))


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
        return (self.type.expr(), self._name)


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
            return (self.type.expr(), self._name)
        item = member(self.type, name).expr()
        if self._base:
            return (item, (".", self._base.expr(self._name), name))
        return (item, (".", (self.type.expr(), self._name), name))


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
            t, b = self._base.expr(self._name)
        else:
            t = self.type.expr()
            b = self._name
        if self.idx is not None:
            i = self.idx.expr()
            rt = self.type.type.expr()
            return (rt, ("[]", (t, b), i))
        else:
            return (t, b)


class _InstanceVar(_Var):
    _VARS = set(("_name", "type", "_builder", "_base"))
    type: _Module

    def __init__(
        self,
        type: _Module,
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
        if isinstance(item, _Port):
            return _vartype(item.type, name, self._builder, self)
        raise TypeError(
            f"Cannot access {name} in instance of {self.type.name}"
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
        assert isinstance(item, _DataMember)
        # TODO: check that member is (part of) output, wire or register
        if isinstance(value, int):
            value = _infer_int(item.type, value)
        if not equivalent(value.type, item.type, False):
            raise TypeError(
                f"Cannot assign non-equivalent type {value.type} to {item.type}"
            )
        self._builder.code.append(("connect", self.expr(name), value.expr()))

    def expr(self, name):
        item = self.type[name]
        return (item.type, (".", "instance", self._name, name))


def _vartype(type, name, builder, base) -> _Var:
    if isinstance(type, _Struct):
        return _StructVar(type, name, builder, base)
    elif isinstance(type, _Array):
        return _ArrayVar(type, name, builder, base)
    elif isinstance(type, _Module):
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


CodeListItemType = Tuple[Any, ...]


class _CodeBuilder:
    """Represents a module when generating code"""

    _VARS = set(("module", "code", "cat", "cvt"))

    def __init__(self, module: _Module):
        self.module = module
        self.code: List[CodeListItemType] = []

    def __getattr__(self, name: str) -> Union[_Var, _ModuleMember, bool]:
        if name not in self.module:
            raise AttributeError(
                f"Module {self.module.name} has no member {name}"
            )
        item = self.module[name]
        if isinstance(item, _ModuleFunc):
            return self.module[name]
        if isinstance(item, _DataMember):
            return _vartype(item.type, name, self, None)
        return False  # pragma: no cover

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
        if not isinstance(item, _DataMember):
            raise TypeError(
                f"Cannot assign value of unsupported type: {value}"
            )
        if isinstance(item, _Port):
            if item.direction != OUTPUT:
                raise TypeError(f"Cannot assign to input {name}")
        elif isinstance(item, _Instance):
            raise TypeError(f"Cannot assign to instance {name}")
        if isinstance(value, int):
            value = _infer_int(item.type, value)
        if not equivalent(value.type, item.type, False):
            raise TypeError(
                f"Cannot assign non-equivalent type {value.type} to {item.type}"
            )
        self.code.append(("connect", (item.type.expr(), name), value.expr()))

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

        f(self.code)
        return "\n".join(text)

    @contextmanager
    def if_stmt(self, expr):
        code = self.code
        self.code = []
        try:
            yield None
        finally:
            code.append(("when", _logic_value(expr).expr(), tuple(self.code)))
            self.code = code

    @contextmanager
    def elif_stmt(self, expr):
        assert self.code[-1][0] in ("when", "else-when")
        code = self.code
        self.code = []
        try:
            yield None
        finally:
            code.append(
                ("else-when", _logic_value(expr).expr(), tuple(self.code))
            )
            self.code = code

    @contextmanager
    def else_stmt(self):
        assert self.code[-1][0] in ("when", "else-when")
        code = self.code
        self.code = []
        try:
            yield None
        finally:
            code.append(("else", tuple(self.code)))
            self.code = code

    def and_expr(self, *ops):
        ops2 = [_logic_value(x) for x in ops]
        return _reduce2(_AndExpr, *ops2)

    def or_expr(self, *ops):
        ops2 = [_logic_value(x) for x in ops]
        return _reduce2(_OrExpr, *ops2)

    def not_expr(self, op):
        return _NotExpr(_logic_value(op))

    def cat(self, *ops):
        """Concatenate bits"""
        return _reduce2(_CatExpr, *ops)

    def cvt(self, op):
        """Convert to signed"""
        return _CvtExpr(op)


def _ports(module: _Module) -> Sequence[tuple]:
    ports = []
    for p in module._iter_types(_Port):
        assert isinstance(p, _Port)
        direction = "input" if p.direction == INPUT else "output"
        ports.append((p.name, direction, p.type.expr()))
    return ports


def _wires(module: _Module) -> Sequence[tuple]:
    wires = []
    for w in module._iter_types(_Wire):
        assert isinstance(w, _Wire)
        wires.append((w.name, w.type.expr()))
    return wires


def _registers(module: _Module) -> Sequence[tuple]:
    regs = []
    for r in module._iter_types(_Register):
        assert isinstance(r, _Register)
        clk = r.clock.name
        if r.reset is None or r.reset is False:
            reset = 0
        else:
            reset = (r.reset.name, r.value)
        regs.append((r.name, r.type.expr(), clk, reset))
    return regs


def _instances(module: _Module) -> Sequence[tuple]:
    instances = []
    for i in module._iter_types(_Instance):
        assert isinstance(i, _Instance)
        cname, mname = i.type.name.split("::")
        instances.append((i.name, cname, mname))
    return instances


def _code(module: _Module) -> Sequence[tuple]:
    b = _CodeBuilder(module)
    for cf in module._iter_types(_ModuleFunc):
        if not cf.converted:
            f, txt = convert(cf.function, module)
            cf.function = f
            cf.converted = True
    for cc in module._iter_types(_ModuleCode):
        if not cc.converted:
            f, txt = convert(cc.function, module)
            cc.function = f
            cc.converted = True
        else:
            f = cc.function
        f(b)
    return b.code


def build(module: _Module, db: dict[str, dict]) -> None:
    """Generate intermediate format for module and add to database"""
    m = dict(
        ports=_ports(module),
        wires=_wires(module),
        registers=_registers(module),
        instances=_instances(module),
        code=_code(module),
    )
    cname, mname = module.name.split("::")
    if "circuits" not in db:
        db["circuits"] = {}
    c = db["circuits"]
    if cname not in c:
        c[cname] = {}
    c[cname][mname] = m
