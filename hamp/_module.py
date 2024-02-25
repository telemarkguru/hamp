"""
Code for the module class and associated features.
"""

from typing import Callable, Union, Dict, Iterator, Optional
from ._hwtypes import (
    _HWType,
    bitsize,
)
from ._db import default, DB, create_module
from ._convert import convert
from ._builder import _CodeBuilder
from copy import deepcopy


AttrData = Union[str, int, dict, list]
AttrType = Dict[str, AttrData]


class _ModuleMemberSetter:
    cb: Callable[["_Module", str], None]

    def __init__(self, cb: Callable[["_Module", str], None]):
        self.cb = cb


class _ModuleMember:
    name: str
    kind: str
    data: Union[tuple, list]

    def __init__(self, name: str, data: Union[tuple, list], db: DB):
        self.name = name
        self.data = data
        self.kind = data[0]
        self.db = db

    def __len__(self) -> int:
        if self.kind == "attribute":
            return len(self.data[1])
        # elif self.kind == "instance":
        #     raise TypeError("Instances has no len()")
        type = self.data[1]
        return bitsize(type)

    def __getattr__(self, name: str) -> _HWType:
        match self.data[1]:
            case ("struct", *_):
                return getattr(_HWType(self.data[1]), name)
        if self.data[0] == "register":
            if name == "clock":
                return self.data[2]
            elif name == "reset":
                rst = self.data[3]
                if rst == 0:
                    return None
                return rst[0]
            elif name == "value":
                rst = self.data[3]
                if rst == 0:
                    return None
                return rst[1]
        raise TypeError(f"Cannot get attribute {name} of {self.kind}")

    @property
    def type(self) -> _HWType:
        if self.kind in ("input", "output", "wire", "register"):
            return _HWType(self.data[1])
        raise TypeError(f"Cannot get type of {self.kind}")

    @property
    def value(self) -> AttrData:
        if self.kind == "attribute":
            return self.data[1]
        raise TypeError(f"Cannot get value of {self.kind}")


class _Module:
    """Represent a module when describing hardware.
    A module encapsulates a unit that can have
    ports, and can contain behavioral code, state,
    wires and instances of other modules.
    """

    _VARS = set(("name", "db", "module", "bld"))
    _RESERVED = set(("cat",))

    db: DB
    name: str
    module: dict
    bld: _CodeBuilder

    def __init__(self, name: str, db: DB):
        """
        Create module API object for given module in database.
        """
        self.name = name
        self.db = db
        cn, mn = name.split("::", 1)
        try:
            self.module = db["circuits"][cn][mn]
        except KeyError:
            raise NameError(f"Module {name} not found in database")
        self.bld = _CodeBuilder(self.name, self.module, self.db)

    def __call__(self, **attributes: AttrData) -> _ModuleMemberSetter:
        """Create and return and instance of this module."""
        circ, modname = self.name.split("::")

        def cb(m, name):
            mod = m.module
            mod["instance"].append(name)
            mod["data"][name] = (
                "instance",
                ("instance", circ, modname),
                attributes,
            )

        return _ModuleMemberSetter(cb)

    def __setattr__(self, name: str, value: _ModuleMemberSetter) -> None:
        """Add ports, wires, states, instances, cod
        or attributes to this module"""
        if name in _Module._VARS:
            super().__setattr__(name, value)
            return
        if name in _Module._RESERVED:
            raise NameError(f"Name {name} is reserved")
        if not isinstance(value, _ModuleMemberSetter):
            raise TypeError(
                f"Cannot add values of type {type(value)} to a module"
            )
        if name in self.module["data"]:
            raise KeyError(
                f"{name} already defined in module {self.name}, "
                "delete first to redefine"
            )
        value.cb(self, name)

    def __delattr__(self, name: str) -> None:
        """Delete member from this module"""
        data = self.module["data"]
        try:
            entry = data[name]
        except KeyError:
            raise AttributeError(f"Module {self.name} has no member {name}")
        kind = entry[0]
        self.module[kind].remove(name)
        del data[name]

    def __getattr__(self, name: str) -> Union[_ModuleMember, "_Module"]:
        """Return member of this module"""
        data = self.module["data"]
        try:
            entry = data[name]
        except KeyError:
            raise AttributeError(f"Module {self.name} has no member {name}")
        kind = entry[0]
        if kind == "instance":
            cn, mn = entry[1][1:3]
            return _Module(f"{cn}::{mn}", self.db)
        return _ModuleMember(name, entry, self.db)

    def __setitem__(self, name: str, value: _ModuleMemberSetter) -> None:
        """Add member to this module"""
        self.__setattr__(name, value)

    def __getitem__(self, name: str) -> _ModuleMember:
        """Return member with the given name (m[name])"""
        return self.__getattr__(name)

    def __delitem__(self, name: str) -> None:
        """Delete member from this module"""
        self.__delattr__(name)

    def __iter__(self) -> Iterator[_ModuleMember]:
        """Iterate over module members, and yield names"""
        for k, v in self.module["data"].items():
            yield _ModuleMember(k, v, self.db)

    def __contains__(self, name: str) -> bool:
        """Return True if the module has a member with the given name, and
        False if not"""
        return name in self.module["data"]

    def clone(self, new_name: str) -> "_Module":
        """Create and return a clone of this module with the given name"""
        if "::" not in new_name:
            new_name = f"{new_name}::{new_name}"
        cn, mn = new_name.split("::", 1)
        circ = self.db["circuits"]
        try:
            circ[cn][mn]
        except KeyError:
            mod = deepcopy(self.module)
            circ.setdefault(cn, {})[mn] = mod
            return _Module(new_name, self.db)
        raise NameError(f"Module {cn}::{mn} already defined")

    def code(self, function: Callable[[_CodeBuilder], None]) -> None:
        """Decorator for adding code to this module, like so:

        @a_module.code
        def data_in(m):
            if m.in_stb:
                m.data = m.in_data

        The decorated function takes a module instance as its
        only parameter, and should not return anything.

        Can also be called directly:
        a_module.code(a_function)
        """
        func, text = convert(function, self.module)
        # print(text)
        func(self.bld)
        return None

    def function(self, function: Callable) -> None:
        """Decorator for adding hardware generating function, like so:

        @a_module.function
        def adder(m, a, b):
            return a + b + m.bias

        The decorated function must take a module bulder instance as its
        first parameter.
        """
        func, text = convert(function, self.module)
        # print(text)
        return func


NULL_DATA_MEMBER = _ModuleMember("null", ["null"], {})


def module(name: str, db: Optional[DB] = None):
    """
    Create a new module with given name.
    Return module API object.
    Use supplied database, or default if not given
    """
    if "::" not in name:
        name = f"{name}::{name}"
    db = db or default
    cn, mn = name.split("::", 1)
    create_module(db, cn, mn)
    return _Module(name, db)


# TODO: Add function to get existing module


def input(type: _HWType, **attributes: AttrData) -> _ModuleMemberSetter:
    """Create input module member of the given type"""

    def cb(m, name):
        mod = m.module
        mod["input"].append(name)
        mod["data"][name] = ("input", type.expr, attributes)

    return _ModuleMemberSetter(cb)


def output(type: _HWType, **attributes: AttrData) -> _ModuleMemberSetter:
    """Create output module member of the given type"""

    def cb(m, name):
        mod = m.module
        mod["output"].append(name)
        mod["data"][name] = ("output", type.expr, attributes)

    return _ModuleMemberSetter(cb)


def wire(type: _HWType, **attributes: AttrData) -> _ModuleMemberSetter:
    """Create wire module member of the given type"""

    def cb(m, name):
        mod = m.module
        mod["wire"].append(name)
        mod["data"][name] = ("wire", type.expr, attributes)

    return _ModuleMemberSetter(cb)


def _find_clock(module: _Module) -> str:
    for name, item in module.module["data"].items():
        if item[1] == ("clock", 1):
            return name
    raise ValueError(f"No clock defined in module {module.name}")


def _find_reset(module: _Module) -> str:
    for name, item in module.module["data"].items():
        if item[1] == ("reset", 1):
            return name
    raise ValueError(f"No reset defined in module {module.name}")


def register(
    type: _HWType,
    clock: _ModuleMember = NULL_DATA_MEMBER,
    reset: _ModuleMember = NULL_DATA_MEMBER,
    value: Union[int, _HWType, None] = None,
    **attributes: AttrData,
) -> _ModuleMemberSetter:
    """Create register module member of the given type.
    The clock is inferred if not specified (the first defined clock
    in the module is used).
    The reset if inferred if not specified (the first defined reset
    in the module is used). If reset is set to False, the regiser
    is not reset.
    The reset value is zero if not specified.
    """

    def cb(m, name):
        mod = m.module
        mod["register"].append(name)
        if clock is NULL_DATA_MEMBER:
            clk = _find_clock(m)
        else:
            clk = clock.name
        if value is not None:
            if reset is NULL_DATA_MEMBER:
                rst = _find_reset(m)
            else:
                rst = reset.name
            rst = (rst, value)
        else:
            rst = 0
        mod["data"][name] = ("register", type.expr, clk, rst, attributes)

    return _ModuleMemberSetter(cb)


def attribute(value: AttrData) -> _ModuleMemberSetter:
    """Create attribute module member (of any type).
    Used to store meta-data that is not converted to RTL.
    """

    def cb(m, name):
        mod = m.module
        mod["attribute"].append(name)
        mod["data"][name] = ("attribute", value)

    return _ModuleMemberSetter(cb)


def unique(name: str, db: Optional[DB] = None) -> str:
    """Generate unique module name based on given base name"""
    db = db or default
    if "::" not in name:
        name = f"{name}::{name}"
    idx = 0
    cn, mn = name.split("::", 1)
    new_mn = mn
    while True:
        try:
            db["circuits"][cn][new_mn]
            idx += 1
            new_mn = f"{mn}_{idx}"
        except KeyError:
            return f"{cn}::{new_mn}"


def instance(name: str, **attributes: AttrData) -> _ModuleMemberSetter:
    """
    Create an instance module member of a module with the given
    name (circuit::module)
    """
    modname = name

    def cb(m, name):
        mod = m.module
        db = m.db
        if "::" not in modname:
            circuits = (m.name.split("::")[0], modname)
            mn = modname
        else:
            c, n = modname.split("::")
            circuits = (c,)
            mn = n
        for circ in circuits:
            try:
                db["circuits"][circ][mn]
                break
            except KeyError:
                continue
        else:
            raise NameError(f"No module named {modname} defined")
        mod["instance"].append(name)
        mod["data"][name] = ("instance", ("instance", circ, mn), attributes)

    return _ModuleMemberSetter(cb)


'''
def ports(m: _Module) -> Iterator[_Port]:
    """Iterate over ports"""
    return m._iter_types(_Port)
'''
