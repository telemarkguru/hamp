"""
Generate module code
"""

from ._module import _Module, _CodeItem
from ._builder import _CodeBuilder
from ._convert import convert


def code(m: _Module) -> _CodeBuilder:
    """Generate code for module"""
    cb = _CodeBuilder(m)
    for _, c in m._iter_types(_CodeItem):
        f, txt = convert(c.function, m)
        f(cb)
    return cb
