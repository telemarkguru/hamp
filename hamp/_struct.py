"""Composit data types"""

from ._hwtypes import hwtype, _HWType
from typing import Iterator, Tuple


def struct(c) -> _HWType:
    """Class decorator to make a class a struct.
    It preprocesses the class members and then
    calls dataclass to generate a dataclass Python class
    """

    c.__flips__ = set()
    fs = []
    for a, t in c.__annotations__.items():
        if isinstance(t, tuple):
            t, _ = t
            flip = 1
        else:
            flip = 0
        if isinstance(t, _HWType):
            fs.append((a, t.expr, flip))
        else:
            raise TypeError(
                f"Type {t} not allowed as struct member. "
                "Only sized uint, sint and structs based on these are allowed."
            )
    return hwtype("struct", *fs)


def flip(type) -> tuple:
    """Make a struct member have the opposite direction when the
    struct is used as input or output, E.g:

        valid: uint[1]
        ready: flip(uint[1])

    """
    return type, True


def _lookup(s: _HWType, name: str) -> tuple:
    assert isinstance(s, _HWType) and s.kind == "struct"
    for x in s.expr[1:]:
        if name == x[0]:
            return x
    raise AttributeError(f"Struct has no member {name}")


def flipped(s: _HWType, name: str) -> bool:
    """Return True if member is flipped"""
    return _lookup(s, name)[2]


def member(s: _HWType, name: str) -> _HWType:
    """
    Return member type
    """
    return hwtype(_lookup(s, name)[1])


def hasmember(s: _HWType, name: str) -> bool:
    """Return True if struct class has member with given name.
    Return False if not.
    """
    try:
        _lookup(s, name)
        return True
    except AttributeError:
        return False


def members(s: _HWType) -> Iterator[Tuple[str, _HWType]]:
    """Iterator over hardware type members, yield tuples with (name, type)"""
    assert isinstance(s, _HWType) and s.kind == "struct"
    for name, type, _ in s.expr[1:]:
        yield name, hwtype(type)
