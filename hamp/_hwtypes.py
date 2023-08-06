"""
Hardware modelling types
"""

from typing import Dict


class _HWType:
    """Base class for all hardware modelling types"""

    pass


class _Clock(_HWType):
    """Clock signal"""

    type = "clock"


class _Reset(_HWType):
    """Generic reset signal"""

    type = "reset"


class _AsyncReset(_Reset):
    """Asynchronous reset signal"""

    type = "asynchonous_reset"


class _SyncReset(_Reset):
    """Synchronous reset signal"""

    type = "synchronous_reset"


class _IntValue:
    """Integer value"""

    def __init__(self, value, type):
        self.value = value
        self.type = type

    # TODO: methods to manipulate value to it becomes useful for creating
    # constants and meta-data


class _Int(_HWType):
    """Inteber base class"""

    def __init__(self, size: int = 1):
        self.size = size
        self._set_min_max(size)

    def __call__(self, value: int = 0):
        if (
            (self._minval is None or value >= self._minval)
            and (self._maxval is None or value <= self._maxval)
        ):
            return _IntValue(value, self)
        raise ValueError(
            f"{self.type}[{self.size}] cannot hold value {value}"
        )


class _UInt(_Int):
    """Unsigned integer"""

    type = "uint"

    def _set_min_max(self, size):
        self._minval = 0
        if size > 0:
            self._maxval = (1 << size) - 1
        else:
            self._maxval = None


class _SInt(_Int):
    """Signed integer"""

    type = "sint"

    def _set_min_max(self, size):
        if size > 0:
            self._minval = - (1 << (self.size-1))
            self._maxval = (1 << self.size-1) - 1
        else:
            self._minval = self._maxval = None


class _IntFactory:
    """Creates intger types"""

    def __init__(self, int_type: type[_Int]):
        self.type: type[_Int] = int_type
        self.types: Dict[int, _Int] = {}
        self.unsized: _Int = int_type(-1)

    def __getitem__(self, size: int):
        """Return integer type of given size.
        Usage examples:
            uint[3]  # 3-bit unsigned integer type
            sint[3](-1)  # 3-bit signed value of -1
        """
        if t := self.types.get(size):
            return t
        t = self.type(size)
        self.types[size] = t
        return t

    def __call__(self, value: int = 0):
        """Create unsized integer value.
        Example:
            uint(4)  # Unsized unsigned integer value of 4
        """
        return self.unsized(value)


class _Struct(_HWType):
    """Struct type"""

    type = "Struct"


class _Direction:
    """Port direction"""

    def __init__(self, name):
        self.name = name


INPUT = _Direction("input")
OUTPUT = _Direction("output")


def clock() -> _Clock:
    """Create and return a clock"""
    return _Clock()


def reset() -> _Reset:
    """Create and return a generic reset, that is converted to a
    synchronous or asynchonous reset when the design is elaborated
    """
    return _Reset()


def async_reset() -> _AsyncReset:
    """Create and return an asynchronous reset"""
    return _AsyncReset()


def sync_reset() -> _SyncReset:
    """Create and return a synchronous reset"""
    return _SyncReset()


uint = _IntFactory(_UInt)
sint = _IntFactory(_SInt)
