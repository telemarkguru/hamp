"""Standard functions"""
from ._builder import ExprType, ExprRType, _value_str


def cat(*vars: ExprType) -> ExprRType:
    """Concatenate values"""
    assert vars

    if len(vars) == 2:
        return ("cat", _value_str(vars[0]), _value_str(vars[1]))
    v, *vv = vars
    return ("cat", _value_str(v), cat(*vv))
