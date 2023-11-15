"""
Convert to FIRRTL
"""

from typing import Dict, Callable
from . import _module as m
from ._generate import code
from ._hwtypes import _IntValue


_op_to_func = {
    "+": "add",
}


def _genfunc(*types):
    """Decorator to create code generator function for type"""

    def f(func):
        for type in types:
            type._firrtl_code = func

    return f


@_genfunc(m._Port)
def _port(p: m._Port, name: str) -> str:
    return f"{p.direction.name} {name} : {p.type.firrtl()}"


@_genfunc(m._Wire)
def _wire(w: m._Wire, name: str) -> str:
    return f"wire {name} : {w.type.firrtl()}"


@_genfunc(m._Register)
def _register(r: m._Register, name: str) -> str:
    if r.reset:
        return f"regreset {name} : {r.type}, {r.clock}, {r.reset}, {r.value}"
    else:
        return f"reg {name} : {r.type}, {r.clock}"


@_genfunc(m._Instance)
def _instance(m: m._Instance, name: str) -> str:
    return f"inst {name} of {m.module}"


def _preamble(version: str = "1.1.0") -> str:
    """Return FIRRTL header"""
    return f"FIRRTL version {version}\ncircuit :\n"


def _module(module: m._Module, prefix: str = "") -> str:
    """Generate and return FIRRTL code for module"""
    ports = _items(module, m._Port)
    data = _items(module, m._LocalDataMember)
    statements = _statements(module)
    return (
        f"  {prefix}module {module.name} :\n"
        f"    {ports}\n"
        f"    {data}\n"
        f"    {statements}\n"
    )


def _items(module: m._Module, *types) -> str:
    """Generate code for item"""
    return "\n    ".join(
        x._firrtl_code(n) for n, x in module._iter_types(*types)
    )


def _statements(module: m._Module) -> str:
    cb = code(module)
    indent = 0
    return "\n    ".join(
        f"{' ' * (indent*4)}{_expr(x)}" for x, indent in cb.iter_with_indent()
    )


def _expr(x) -> str:
    if isinstance(x, _IntValue):
        return x.firrtl()
    if not isinstance(x, (tuple, list)):
        return x
    if x[0] == "connect":
        return f"connect {x[1]}, {_expr(x[2])}"
    else:
        e = ", ".join(_expr(z) for z in x[1:])
        f = _op_to_func.get(x[0], x[0])
        return f"{f}({e})"


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
