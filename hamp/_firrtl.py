"""
Convert to FIRRTL
"""

from . import _module as m
from ._generate import code
from ._hwtypes import _IntValue, _Reset, _Clock
from ._hwtypes_firrtl import apply
from typing import Union


apply()


def _d_if_not_int(x):
    return "d" if not isinstance(x, int) else ""


def _op1(name, argc=1, parc=0):
    return (f"{name}({{e[0]}})", argc, parc)


def _op2(name, argc=2, parc=0):
    return (f"{name}({{e[0]}}, {{e[1]}})", argc, parc)


def _op3(name, argc=3, parc=0):
    return (f"{name}({{e[0]}}, {{e[1]}}, {{e[2]}})", argc, parc)


def _int(t):
    return (f"{t}({{e[1]}})", 1, 1)


_op_to_func = {
    # op -> opstr, argument count, parameter count
    "+": _op2("add"),
    "-": _op2("sub"),
    "*": _op2("mul"),
    "//": _op2("div"),
    "%": _op2("rem"),
    "==": _op2("eq"),
    "!=": _op2("neq"),
    ">": _op2("gt"),
    ">=": _op2("geq"),
    "<": _op2("lt"),
    "<=": _op2("leq"),
    ">>": _op2("dshr"),
    "<<": _op2("dshl"),
    ">>k": _op2("shr", 1, 1),
    "<<k": _op2("shl", 1, 1),
    "&": _op2("and"),
    "|": _op2("or"),
    "^": _op2("xor"),
    "~": _op1("not"),
    "and": _op2("and"),
    "or": _op2("or"),
    "not": _op1("not"),
    "andr": _op1("andr"),
    "orr": _op1("orr"),
    "xorr": _op1("xorr"),
    "cat": _op2("cat"),
    "bits": _op3("bits", 1, 2),
    ".": ("{e[0]}.{e[1]}", 2, 0),
    "[]": ("{e[0]}[{e[1]}]", 2, 0),
    "uint": _int("UInt"),
    "sint": _int("SInt"),
}


def _genfunc(*types):
    """Decorator to create code generator function for type"""

    def f(func):
        for type in types:
            type._firrtl_code = func

    return f


@_genfunc(m._Port)
def _port(p: m._Port) -> str:
    return f"{p.direction.name} {p.name} : {p.type.firrtl()}"


@_genfunc(m._Wire)
def _wire(w: m._Wire) -> str:
    return f"wire {w.name} : {w.type.firrtl()}"


@_genfunc(m._Register)
def _register(r: m._Register) -> str:
    type = r.type.firrtl()
    if isinstance(r.reset, m._DataMember):
        assert isinstance(r.reset.type, _Reset)
        reset = f" with: (reset => ({r.reset.name}, {type}({r.value})))"
    else:
        reset = ""
    assert isinstance(r.clock, m._DataMember)
    assert isinstance(r.clock.type, _Clock)
    return f"reg {r.name} : {type}, {r.clock.name}{reset}"


@_genfunc(m._Instance)
def _instance(m: m._Instance) -> str:
    return f"inst {m.name} of {m.module.name}"


def _preamble(name: str, version: str = "1.1.0") -> str:
    """Return FIRRTL header"""
    return f"FIRRTL version {version}\ncircuit {name} :\n"


def _module(module: m._Module, prefix: str = "") -> str:
    """Generate and return FIRRTL code for module"""
    ports = _items(module, m._Port)
    data = _items(module, m._LocalDataMember)
    statements = _statements(module)
    return (
        "\n"
        f"  {prefix}module {module.name} :\n"
        f"    {ports}\n"
        "\n"
        f"    {data}\n"  # Wires, registers and instances
        "\n"
        f"    {statements}\n"
    )


def _items(module: m._Module, *types) -> str:
    """Generate code for item"""
    return "\n    ".join(x._firrtl_code() for x in module._iter_types(*types))


def _statements(module: m._Module) -> str:
    cb = code(module)
    lines = [(indent, _expr(x)) for x, indent in cb.iter_with_indent()]
    return "\n    ".join(
        f"{' ' * (indent*4)}{expr}" for indent, expr in lines if expr
    )


def _expr(x, signed=False) -> Union[str, int]:
    if isinstance(x, int):
        return x
    if isinstance(x, _IntValue):
        return x.firrtl()
    if not isinstance(x, (tuple, list)):
        return str(x)
    op = x[0]
    if op == "connect":
        return f"{_expr(x[1])} <= {_expr(x[2])}"
    elif op == "when":
        return f"when {_expr(x[1])} :"
    elif op == "else":
        return "else :"
    elif op == "else_when":
        return f"else when {_expr(x[1])} :"
    elif op == "end_when":
        return ""
    elif op in ("<<", ">>") and isinstance(x[2], int):
        opstr, _, _ = _op_to_func[f"{op}k"]
        return opstr.format(e=[_expr(x[1]), x[2]])
    else:
        opstr, argc, parc = _op_to_func[op]
        e = [_expr(z) if i < argc else z for i, z in enumerate(x[1:])]
        f = opstr.format(e=e)
        return f


def generate(*modules):
    """
    Generate and return FIRRTL code for given modules.
    First module is public, the rest are private
    """
    name = modules[0].name
    return _preamble(name) + "\n".join((_module(x) for x in modules))
