"""
Show data types as strings
"""

from ._db import TL


def show_type(type: TL) -> str:
    match type:
        case ("uint", int(x)):
            return f"uint[{x}]"
        case ("sint", int(x)):
            return f"sint[{x}]"
        case ("clock", 1) | ("reset", 1) | ("async_reset", 1):
            return type[0]
        case ("array", int(x), type):
            return f"{show_type(type)}[{x}]"
        case ("struct", *fields):
            return (
                "{"
                + ", ".join(
                    f"{x[0]}: {'flip ' if x[2] else ''}{show_type(x[1])}"
                    for x in fields
                )
                + "}"
            )
        case _:
            raise ValueError(f"Malformed type: {type}")


def show_expr(expr: TL) -> str:
    match expr:
        case _, int(x):
            return f"{x:#x}"
        case _, str(x):
            return x
        case _, (".", (type, var), str(x)):
            if type[0] == "struct":
                return f"{show_expr((type, var))}.{x}"
            else:
                return f"{var}.{x}"
        case _, ("[]", (type, var), val):
            return f"{show_expr((type, var))}[{show_expr(val)}]"
        case _, (str(op), *args):
            argstrs = []
            for a in args:
                match a:
                    case (type, value):
                        argstrs.append(show_expr((type, value)))
                    case _:
                        raise ValueError(f"Malformed op argument: {a}")
            return f"{op}({', '.join(argstrs)})"
        case _, dict(x):
            return (
                "{"
                + ", ".join(f"{k}: {show_expr(v)}" for k, v in x.items())
                + "}"
            )
        case _, list(x):
            return "[" + ", ".join(show_expr(v) for v in x) + "]"
        case _:
            raise ValueError(f"Malformed expression: {expr}")
