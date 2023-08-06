"""Composit data types"""

from dataclasses import dataclass, field
from ._hwtypes import uint, sint, _Int


def struct(c):
    """Class decorator to make a class a struct.
    It preprocesses the class members and then
    calls dataclass to generate a dataclass Python class
    """
    annotations = c.__annotations__
    c.__flips__ = set()
    for a in annotations:
        t = annotations[a]
        if isinstance(t, tuple):
            t, _ = t
            c.__flips__.add(a)
        if isinstance(t, _Int):
            if not hasattr(c, a):
                setattr(c, a, t(0))
        elif hasattr(t, "__hamp_struct__"):
            if not hasattr(c, a):
                setattr(c, a, field(default_factory=t))
        else:
            raise TypeError(
                f"Type {t} not allowed as struct member. "
                "Only sized uint, sint and structs based on these are allowed."
            )
    c.__hamp_struct__ = True
    return dataclass(c)


def flip(type):
    """Make a struct member have the opposite direction when the
    struct is used as input or output, E.g:

        valid: uint[1]
        ready: flip(uint[1])

    """
    return type, True
