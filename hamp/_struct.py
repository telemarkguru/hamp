"""Composit data types"""

from dataclasses import dataclass, field, fields
from ._hwtypes import _Int, _Struct, _Array, _HWType
from typing import Union, Iterator, Tuple


def struct(c):
    """Class decorator to make a class a struct.
    It preprocesses the class members and then
    calls dataclass to generate a dataclass Python class
    """

    c.__flips__ = set()
    for a, t in c.__annotations__.items():
        if isinstance(t, tuple):
            t, _ = t
            c.__flips__.add(a)
            c.__annotations__[a] = t
        if isinstance(t, _Int):
            if not hasattr(c, a):
                setattr(c, a, t(0))
        elif hasattr(t, "__hamp_struct__"):
            if not hasattr(c, a):
                setattr(c, a, field(default_factory=t))
        elif isinstance(t, _Array):
            if not hasattr(c, a):
                setattr(c, a, field(default_factory=t))
        else:
            raise TypeError(
                f"Type {t} not allowed as struct member. "
                "Only sized uint, sint and structs based on these are allowed."
            )
    c.__hamp_struct__ = True
    return _Struct(dataclass(c))


def flip(type):
    """Make a struct member have the opposite direction when the
    struct is used as input or output, E.g:

        valid: uint[1]
        ready: flip(uint[1])

    """
    return type, True


def flipped(s: _Struct, name: str) -> bool:
    """Return True if member is flipped"""
    assert isinstance(s, _Struct)
    return name in s.dataclass.__flips__


def member(s: _Struct, name: str) -> Union[type, None]:
    """Return member type if struct class has member with given name.
    Return None if not.
    """
    assert isinstance(s, _Struct)
    m = s.dataclass.__annotations__.get(name)
    if m is None:
        raise AttributeError(f"Struct {s} has no member {name}")
    return m


def hasmember(s: _Struct, name: str) -> bool:
    """Return True if struct class has member with given name.
    Return False if not.
    """
    return member(s, name) is not None


def members(s: _Struct) -> Iterator[Tuple[str, _HWType]]:
    """Iterator over hardware type members, yield tuples with (name, type)"""
    assert isinstance(s, _Struct)
    for f in fields(s.dataclass):
        t = f.type
        if isinstance(t, _HWType):
            yield f.name, t
