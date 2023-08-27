"""
Code for the module class and associated features.
"""

from typing import Callable, Union, Any, Dict
from ._hwtypes import (
    _HWType,
    _Clock,
    _Reset,
    _Direction,
    INPUT,
    OUTPUT,
)
from copy import deepcopy


modules: Dict[str, "_Module"] = {}


class _ModuleMember:
    """Base class for module members (ports, wires, state, code)"""

    def clone(self) -> "_ModuleMember":
        return deepcopy(self)


def _is_clock_input(i):
    return (
        isinstance(i, _Port)
        and i.direction == INPUT
        and isinstance(i.type, _Clock)
    )


def _is_reset_input(i):
    return (
        isinstance(i, _Port)
        and i.direction == INPUT
        and isinstance(i.type, _Reset)
    )


class _Module:
    """Represent a module when describing hardware.
    A module encapsulates a unit that can have
    ports, and can contain behavioral code, state,
    wires and instances of other modules.
    """

    _VARS = set(("name", "_members"))

    def __init__(self, name: str):
        """Create an empty module.
        Ports, behavioral code, wires, state and instances are
        added after the module has been created.
        This makes it easy to create and mainpulate modules
        programatically.
        """
        if name in modules:
            raise NameError(f"Redefinition of module {name}")
        self.name: str = name
        self._members: Dict[str, _ModuleMember] = {}
        modules[name] = self

    def __call__(self) -> "_Instance":
        """Create and return and instance of this module."""
        return _Instance(self)

    def __setattr__(self, name: str, value: _ModuleMember) -> None:
        """Add ports, wires, states, instances, cod
        or attributes to this module"""
        if name in _Module._VARS:
            super().__setattr__(name, value)
            return
        if not isinstance(value, _ModuleMember):
            raise TypeError(
                f"Cannot add values of type {type(value)} to a module"
            )
        if name in self._members:
            raise KeyError(f"{name} already defined in module {self.name}")
        self._members[name] = value
        if isinstance(value, _Register):
            if value.clock is None:
                value.clock = self._find_clock()
            if value.reset is None:
                value.reset = self._find_reset()
        elif isinstance(value, _Instance):
            value.name = name

    def __delitem__(self, name: str) -> None:
        """Delete member from this module"""
        del self._members[name]

    def __getattr__(self, name: str) -> _ModuleMember:
        """Return member of this module"""
        return self._members[name]

    def __setitem__(self, name: str, value: _ModuleMember) -> None:
        """Add member to this module"""
        self.__setattr__(name, value)

    def __getitem__(self, name: str) -> _ModuleMember:
        """Reutrn member with the given name (m[name])"""
        return self._members[name]

    def __iter__(self):
        """Iterate over module members"""
        return iter(self._members)

    def __contains__(self, name: str) -> bool:
        """Return True if the module has a member with the given name, and
        False if not"""
        return name in self._members

    def attr(self, name) -> Any:
        """Return an value of attribute with the given name"""
        m = self._members[name]
        if not isinstance(m, _Attribute):
            raise KeyError(f"Module member {name} is not an attribute" "")
        return m.value

    def clone(self, new_name: str) -> "_Module":
        """Create and return a clone of this module with the given name"""
        module = _Module(new_name)
        for name in self._members:
            m = self._members[name]
            module.__setattr__(name, m.clone())
        return module

    def _find_clock(self):
        for name in self._members:
            m = self._members[name]
            if _is_clock_input(m):
                return m
        raise ValueError(f"No clock defined in module {self.name}")

    def _find_reset(self):
        for name in self._members:
            m = self._members[name]
            if _is_reset_input(m):
                return m
        raise ValueError(f"No clock defined in module {self.name}")

    def code(self, function: Callable[["_Instance"], None]) -> None:
        """Decorator for adding code to this module, like so:

        @a_module.code
        def data_in(m):
            if m.in_stb:
                m.data = m.in_data

        The decorated function takes a module instance as its
        only parameter, and should not return anything.

        The functions is stored wrapped as a member of the module
        and is named as the function decorated.

        Can also be called directly:
        a_module.code(a_function)
        """
        self.__setattr__(function.__name__, _ModuleCode(function))

    def function(self, function: Callable) -> None:
        """Decorator for adding hardware generating function, like so:

        @a_module.function
        def adder(m, a, b):
            return a + b + m.bias

        The decorated function must take a module bulder instance as its
        first parameter.
        """
        self.__setattr__(function.__name__, _ModuleFunc(function))


class _Instance(_ModuleMember):
    """Module instance module member"""

    name: str

    def __init__(self, module: _Module):
        self.module = module
        self.name = ""

    def __getattr__(self, name) -> "_Port":
        """Return module port"""
        m = getattr(self.module, name)
        if not isinstance(m, _Port):
            raise TypeError(
                f"Member {name} of module {self.module.name} is not a port"
            )
        return m


class _ModuleCode(_ModuleMember):
    """Code module member"""

    def __init__(self, function: Callable[[_Instance], None]):
        self.function = function


class _ModuleFunc(_ModuleMember):
    """Function module member"""

    def __init__(self, function: Callable):
        self.function = function


class _Port(_ModuleMember):
    """Port module member"""

    def __init__(self, type: _HWType, direction: _Direction):
        self.type = type
        self.direction = direction


class _Wire(_ModuleMember):
    """Wire module member"""

    def __init__(self, type: _HWType):
        self.type = type


class _Register(_ModuleMember):
    """State module member"""

    def __init__(
        self,
        type: _HWType,
        clock: Union[_Clock, None],
        reset: Union[_Reset, None, bool],
        value: Union[int, _HWType],
    ):
        self.type = type
        self.clock = clock
        self.reset = reset
        self.value = value

    # TODO: Add attributes to registers to make it possible to
    # annotate CSR info to a register


class _Attribute(_ModuleMember):
    """Attribute module member"""

    def __init__(self, value: Any):
        self.value = value


# Syntactic sugar:

# "Function" creating a module:
module = _Module


def input(type: _HWType) -> _Port:
    """Create input module member of the given type"""
    return _Port(type, INPUT)


def output(type: _HWType) -> _Port:
    """Create output module member of the given type"""
    return _Port(type, OUTPUT)


def wire(type: _HWType) -> _Wire:
    """Create wire module member of the given type"""
    return _Wire(type)


def register(
    type: _HWType,
    clock: Union[_Clock, None] = None,
    reset: Union[_Reset, None, bool] = None,
    value: Union[int, _HWType] = 0,
) -> _Register:
    """Create register module member of the given type.
    The clock is inferred if not specified (the first defined clock
    in the module is used).
    The reset if inferred if not specified (the first defined reset
    in the module is used). If reset is set to False, the regiser
    is not reset.
    The reset value is zero if not specified.
    """
    return _Register(type, clock, reset, value)


def attribute(value: Any):
    """Create attribute module member (of any type).
    Used to store meta-data that is not converted to RTL.
    """
    return _Attribute(value)


def unique(name: str) -> str:
    """Generate unique module name based on given base name"""
    new_name = name
    idx = 0
    while new_name in modules:
        idx += 1
        new_name = f"{name}_{idx}"
    return new_name


def instance(name: str) -> _Instance:
    """Create an instance of a module with the given name"""
    if not (m := modules.get(name)):
        raise NameError(f"No module named {name} defined")
    return m()
