"""
Convert to FIRRTL
"""

from typing import Dict, Callable
from . import _module as m
from ._generate import code
from ._hwtypes import _IntValue


def _d_if_not_int(x):
    return "d" if not isinstance(x, int) else ""


_op_to_func = {
    "+": "add({e[0]}, {e[1]})",
    "-": "sub({e[0]}, {e[1]})",
    "*": "mul({e[0]}, {e[1]})",
    "%": "rem({e[0]}, {e[1]})",
    "==": "eq({e[0]}, {e[1]})",
    "!=": "neq({e[0]}, {e[1]})",
    ">": "gt({e[0]}, {e[1]})",
    ">=": "geq({e[0]}, {e[1]})",
    "<": "lt({e[0]}, {e[1]})",
    "<=": "leq({e[0]}, {e[1]})",
    ">>": "{d}shr({e[0]}, {e[1]})",
    "<<": "{d}shl({e[0]}, {e[1]})",
    "&": "and({e[0]}, {e[1]})",
    "|": "or({e[0]}, {e[1]})",
    "^": "xor({e[0]}, {e[1]})",
    "~": "not({e[0]})",
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
    if r.reset:
        return (
            f"regreset {r.name} : {r.type.firrtl()}, {r.clock.name}, "
            f"{r.reset.name}, {r.value}"
        )
    else:
        return f"reg {r.name} : {r.type.firrtl()}, {r.clock.name}"


@_genfunc(m._Instance)
def _instance(m: m._Instance) -> str:
    return f"inst {m.name} of {m.module}"


def _preamble(version: str = "1.1.0") -> str:
    """Return FIRRTL header"""
    return f"FIRRTL version {version}\ncircuit :\n"


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
    indent = 0
    lines = [(indent, _expr(x)) for x, indent in cb.iter_with_indent()]
    return "\n    ".join(
        f"{' ' * (indent*4)}{expr}" for indent, expr in lines if expr
    )


def _expr(x) -> str:
    if isinstance(x, int):
        if x >= 0:
            return f"UInt({x})"
        else:
            return f"SInt({x})"
    if isinstance(x, _IntValue):
        return x.firrtl()
    if not isinstance(x, (tuple, list)):
        return str(x)
    op = x[0]
    if op == "connect":
        return f"connect {x[1]}, {_expr(x[2])}"
    elif op == "when":
        return f"when {_expr(x[1])} :"
    elif op == "else":
        return "else :"
    elif op == "else_when":
        return f"else when {_expr(x[1])} :"
    elif op == "end_when":
        return ""
    else:
        e = [_expr(z) for z in x[1:]]
        d = "d" if len(e) > 1 and not isinstance(e[1], int) else ""
        f = _op_to_func[op].format(e=e, d=d)
        return f


def generate(*modules):
    """
    Generate and return FIRRTL code for given modules.
    First module is public, the rest are private
    """
    return (
        _preamble()
        + _module(modules[0], "public ")
        + "\n".join((_module(x) for x in modules[1:]))
    )
