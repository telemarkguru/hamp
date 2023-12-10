"""
Generate module code
"""

from ._module import _Module, _ModuleCode, _ModuleFunc
from ._builder import _CodeBuilder
from ._convert import convert


def code(m: _Module) -> _CodeBuilder:
    """Generate code for module"""
    cb = _CodeBuilder(m)

    for cf in m._iter_types(_ModuleFunc):
        if not cf.converted:
            f, txt = convert(cf.function, m)
            cf.function = f
            cf.converted = True
    for cc in m._iter_types(_ModuleCode):
        if not cc.converted:
            f, txt = convert(cc.function, m)
            cc.function = f
            cc.converted = True
        else:
            f = cc.function
        f(cb)
    return cb
