"""
FIRRTL generation for hwtypes
"""

from . import _hwtypes as hw
from dataclasses import fields


def _apply(type):
    def f(func):
        setattr(type, func.__name__, func)

    return f


def _flip(s, m):
    return "flip " if m in s.__flips__ else ""


def apply():
    @_apply(hw._HWType)
    def firrtl(self) -> str:
        assert False
        return ""

    @_apply(hw._Clock)
    def firrtl(self) -> str:
        return "Clock"

    @_apply(hw._Reset)
    def firrtl(self) -> str:
        return "Reset"

    @_apply(hw._AsyncReset)
    def firrtl(self) -> str:
        return "AsyncReset"

    @_apply(hw._SyncReset)
    def firrtl(self) -> str:
        return "SyncReset"

    @_apply(hw._IntValue)
    def firrtl(self) -> str:
        return f'{self.type.firrtl()}("h{self.value:#x}")'

    @_apply(hw._UInt)
    def firrtl(self) -> str:
        return f"UInt<{self.size}>"

    @_apply(hw._SInt)
    def firrtl(self) -> str:
        return f"SInt<{self.size}>"

    @_apply(hw._Array)
    def firrtl(self) -> str:
        return f"{self.type.firrtl()}[{self.size}]"

    @_apply(hw._Struct)
    @classmethod
    def firrtl(self) -> str:
        return (
            "{"
            + ", ".join(
                f"{_flip(self, x.name)}{x.name}: {x.type.firrtl()}"
                for x in fields(self)
            )
            + "}"
        )
