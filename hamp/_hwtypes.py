"""
Hardware modelling types
"""

from typing import Dict, Union
from ._show import show_type


def bitsize(type: Union[tuple, list]) -> int:
    match type:
        case ("uint", int(x)):
            return x
        case ("sint", int(x)):
            return x
        case ("clock", 1) | ("reset", 1) | ("async_reset", 1):
            return 1
        case ("array", int(x), type):
            return x * bitsize(type)
        case ("struct", *fields):
            return sum(bitsize(x[1]) for x in fields)
        case _:
            raise ValueError(f"Malformed type: {type}")


def equal(t1: Union[tuple, list], t2: Union[tuple, list], sizes=True) -> bool:
    match t1, t2:
        case ("uint", int(x)), ("uint", int(y)):
            return not sizes or x == y
        case ("sint", int(x)), ("sint", int(y)):
            return not sizes or x == y
        case ("clock", 1), ("clock", 1):
            return True
        case ("reset", 1), ("reset", 1):
            return True
        case ("async_reset", 1), ("async_reset", 1):
            return True
        case ("array", int(x), t1), ("array", int(y), t2):
            return x == y and equal(t1, t2)
        case ("struct", *fields1), ("struct", *fields2):
            return len(fields1) == len(fields2) and all(
                t1[0] == t2[0] and equal(t1[1], t2[1])
                for t1, t2 in zip(fields1, fields2)
            )
        case _:
            return False


class _HWType:
    """Base class for all hardware modelling types"""

    _bitsize: int
    _maxval: int
    _minval: int
    expr: Union[tuple, list]

    def __init__(self, *params):
        if len(params) == 1:
            self.expr = params[0]
        else:
            self.expr = params
        self._bitsize = -1  # Unknonw

    def __getitem__(self, size: int) -> "_HWType":
        """Create array type"""
        return hwtype("array", size, self.expr)

    def __getattr__(self, field: str) -> "_HWType":
        """Get field type of struct"""
        if self.kind == "struct":
            for n, t, _ in self.expr[1:]:
                if field == n:
                    return hwtype(t)
            raise AttributeError(f"Struct has no field {field}")
        else:
            raise TypeError(f"Cannot get field from {self.kind}")

    def __len__(self):
        if self._bitsize > -1:
            return self._bitsize
        self._bitsize = bitsize(self.expr)
        return self._bitsize

    def __eq__(self, x):
        return equal(self.expr, x.expr)

    @property
    def kind(self):
        return self.expr[0]

    @property
    def type(self):
        """return underlying type of array"""
        if self.kind == "array":
            return hwtype(self.expr[2])
        else:
            raise TypeError(f"Cannot get underlaying type of {self.kind}")

    @property
    def size(self):
        if self.kind == "array":
            return self.expr[1]
        else:
            raise TypeError(f"Cannot get size of {self.kind}, use len()")

    @property
    def signed(self):
        return self.kind == "sint"

    def __str__(self):
        return show_type(self.expr)

    def __repr__(self):
        return show_type(self.expr)

    def __call__(self, *args, **kwargs):
        return hwvalue(self.expr, *args, **kwargs)


_hwtype_cache: dict[int, _HWType] = {}


def hwtype(*expr) -> _HWType:
    """
    Create hwtype from expression tuple.
    Use caching on id of tuple.
    """
    if len(expr) > 1:
        h = _HWType(*expr)
        eid = id(h.expr)
        _hwtype_cache[eid] = h
        return h
    eid = id(expr[0])
    if h := _hwtype_cache.get(eid):
        return h
    h = _hwtype_cache[eid] = _HWType(*expr)
    return h


_min_max_cache: dict[tuple, tuple[int, int]] = {}


def _min_max(type: (str, int)) -> (int, int):
    if x := _min_max_cache.get(type):
        return x
    size = type[1]
    if type[0] == "uint":
        minv = 0
        if size > 0:
            maxv = (1 << size) - 1
        else:
            maxv = None
    else:
        if size > 0:
            maxv = (1 << (size - 1)) - 1
            minv = -maxv - 1
        else:
            maxv = None
            minv = None
    _min_max_cache[type] = minv, maxv
    return minv, maxv


def hwvalue(type: tuple, *args, **kwargs):
    """
    Return value for given type
    """
    k = type[0]
    if k == "uint":
        value = args[0] if args else 0
        minv, maxv = _min_max(type)
        if value < minv or maxv is not None and value > maxv:
            size = type[1]
            raise ValueError(f"uint[{size}] cannot hold the value {value:#x}")
    elif k == "sint":
        value = args[0] if args else 0
        minv, maxv = _min_max(type)
        if minv is not None and (value < minv or value > maxv):
            size = type[1]
            raise ValueError(f"sint[{size}] cannot hold the value {value:#x}")
    elif k == "array":
        t = type[2]
        s = type[1]
        args = args[:s]
        value = [hwvalue(t, x) for x in args] + [
            hwvalue(t) for _ in range(s - len(args))
        ]
    elif k == "struct":
        if args and isinstance(args[0], dict):
            kw = args[0]
            kw.update(kwargs)
        else:
            kw = kwargs
        value = {
            k: hwvalue(t, v) if (v := kw.get(k)) else hwvalue(t)
            for k, t, _ in type[1:]
        }
    else:
        value = args and args[0] or 0
        if value not in (0, 1):
            raise ValueError(f"{k} cannot hold the value {value:#x}")
    return value


class _IntFactory:
    """Creates intger types"""

    def __init__(self, kind: str):
        self.kind = kind
        self.types: Dict[int, _HWType] = {}
        self.unsized = hwtype(kind, 0)
        self.unsized._maxval = None
        if kind == "uint":
            self.unsized._minval = 0
        else:
            self.unsized._minval = None

    def __getitem__(self, size: int) -> _HWType:
        """Return integer type of given size.
        Usage examples:
            u1 = uint[1]  # u1 is the unsigned 1 bit integer type
            uint[3]  # 3-bit unsigned integer type
            sint[3](-1)  # 3-bit signed value of -1
        """
        if t := self.types.get(size):
            return t
        t = self.types[size] = hwtype(self.kind, size)
        if self.kind == "uint":
            t._maxval = (1 << size) - 1
            t._minval = 0
        else:
            t._maxval = (1 << (size - 1)) - 1
            t._minval = -t._maxval - 1
        return t

    def __call__(self, value: int = 0):
        """Create unsized integer value.
        Example:
            uint(4)  # Unsized unsigned integer value of 4
        """
        return hwvalue(self.unsized.expr, value)


def equivalent(t1, t2, sizes=True) -> bool:
    """Check if two types are equivalent"""
    if not isinstance(t1, _HWType) or not isinstance(t2, _HWType):
        raise TypeError()
    return equal(t1.expr, t2.expr, sizes)


clock = hwtype("clock", 1)
reset = hwtype("reset", 1)
async_reset = hwtype("async_reset", 1)
sync_reset = hwtype("sync_reset", 1)

uint = _IntFactory("uint")
sint = _IntFactory("sint")
u1 = uint[1]
