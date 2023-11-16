"""
Generate module code
"""

from ._module import _Module, _ModuleCode, _ModuleFunc
from ._builder import _CodeBuilder
from ._convert import convert


def code(m: _Module) -> _CodeBuilder:
    """Generate code for module"""
    cb = _CodeBuilder(m)

    for c in m._iter_types(_ModuleFunc):
        if not c.converted:
            f, txt = convert(c.function, m)
            c.function = f
            c.converted = True
    for c in m._iter_types(_ModuleCode):
        if not c.converted:
            f, txt = convert(c.function, m)
            c.function = f
            c.converted = True
        else:
            f = c.function
        f(cb)
    return cb
