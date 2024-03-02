"""
Convert to FIRRTL
"""
from typing import Optional
import os
from subprocess import run
from contextlib import chdir
from ._db import DB, default


def _op1(name, argc=1, parc=0):
    return (f"{name}({{e[0]}})", argc, parc)


def _op2(name, argc=2, parc=0):
    return (f"{name}({{e[0]}}, {{e[1]}})", argc, parc)


def _op3(name, argc=3, parc=0):
    return (f"{name}({{e[0]}}, {{e[1]}}, {{e[2]}})", argc, parc)


def _int(t):
    return (f"{t}({{e[1]}})", 1, 1)


_op_to_func = {
    # op -> opstr, argument count, parameter count
    "+": _op2("add"),
    "-": _op2("sub"),
    "*": _op2("mul"),
    "//": _op2("div"),
    "%": _op2("rem"),
    "==": _op2("eq"),
    "!=": _op2("neq"),
    ">": _op2("gt"),
    ">=": _op2("geq"),
    "<": _op2("lt"),
    "<=": _op2("leq"),
    ">>": _op2("dshr"),
    "<<": _op2("dshl"),
    ">>k": _op2("shr", 1, 1),
    "<<k": _op2("shl", 1, 1),
    "&": _op2("and"),
    "|": _op2("or"),
    "^": _op2("xor"),
    "~": _op1("not"),
    "and": _op2("and"),
    "or": _op2("or"),
    "not": _op1("not"),
    "andr": _op1("andr"),
    "orr": _op1("orr"),
    "xorr": _op1("xorr"),
    "cat": _op2("cat"),
    "pad": _op2("pad", 1, 1),
    "bits": _op3("bits", 1, 2),
    ".": ("{e[0]}.{e[1]}", 1, 1),
    "[]": ("{e[0]}[{e[1]}]", 2, 0),
    "uint": _int("UInt"),
    "sint": _int("SInt"),
}


def _preamble(version: str = "4.2.0") -> str:
    """Return FIRRTL header"""
    return f"FIRRTL version {version}"


def _expr(x: tuple, k=False) -> str:
    if isinstance(x, str) and k:
        return x
    t, v = x
    match v:
        case str(v):
            return v
        case int(v):
            if k:
                return str(v)
            else:
                return f"{_type(t)}({v})"
        case (str(op), *args):
            if op in ("<<", ">>") and isinstance(args[1][1], int):
                opstr, _, _ = _op_to_func[f"{op}k"]
                return opstr.format(e=[_expr(args[0]), args[1][1]])
            else:
                opstr, argc, parc = _op_to_func[op]
                e = [_expr(z, i >= argc) for i, z in enumerate(args)]
                f = opstr.format(e=e)
                return f
        case _:  # pragma: no cover
            assert False, f"t={t},  v={v}"


def _type(t: tuple) -> str:
    match t:
        case ("uint", int(size)):
            if size > 0:
                return f"UInt<{size}>"
            return "UInt"
        case ("sint", int(size)):
            if size > 0:
                return f"SInt<{size}>"
            return "SInt"
        case ("array", int(size), at):
            return f"{_type(at)}[{size}]"
        case ("struct", *fields):
            return "{" + ", ".join(_type_field(*f) for f in fields) + "}"
        case ("clock", 1):
            return "Clock"
        case ("async_reset", 1):
            return "AsyncReset"
        case ("reset", 1):
            return "AsyncReset"
        case _:  # pragma no cover
            assert False, f"t={t}"


def _type_field(name: str, type: tuple, flip) -> str:
    flip = "flip " if flip else ""
    return f"{flip}{name}: {_type(type)}"


def _register(name, r):
    type = _type(r[1])
    if r[3] == 0:
        return f"    reg {name} : {type}, {r[2]}"
    else:
        rname, rval = r[3]
        return f"    regreset {name} : {type}, {r[2]}, {rname}, {_expr((r[1], rval))}"


def _statements(code: list[tuple], lines: list[str]) -> None:
    def f(code, indent=""):
        for c in code:
            match c:
                case ("when", expr, statements):
                    lines.append(f"{indent}when {_expr(expr)} :")
                    f(statements, indent + "    ")
                case ("else-when", expr, statements):
                    lines.append(f"{indent}else when {_expr(expr)} :")
                    f(statements, indent + "    ")
                case ("else", statements):
                    lines.append(f"{indent}else :")
                    f(statements, indent + "    ")
                case ("connect", target, value):
                    lines.append(f"{indent}{_expr(target)} <= {_expr(value)}")
                case _:  # pragma: no cover
                    assert False

    f(code, "    ")


def _memory(name: str, attr: dict, lines: list[str]) -> None:
    readers = [f"        reader => {x}" for x in attr["_readers"]]
    writers = [f"        writer => {x}" for x in attr["_writers"]]
    readwriters = [f"        readwriter => {x}" for x in attr["_readwriters"]]
    lines += [
        f"    mem {name} :",
        f"        data-type => {_type(attr['_type'])}",
        f"        depth => {attr['_depth']}",
        *readers,
        *writers,
        *readwriters,
        f"        read-latency => {attr.get('_rlat', 1)}",
        f"        write-latency => {attr.get('_wlat', 1)}",
        "        read-under-write => undefined",
    ]


def _module(cname: str, mname: str, db: DB, lines: list[str]) -> None:
    """Generate FIRRTL code for module"""
    pub = "public " if mname == cname else ""
    lines += ["", f"  {pub}module {mname} :"]
    m = db["circuits"][cname][mname]
    data = m["data"]
    for pdir in ("input", "output"):
        for pname in m[pdir]:
            p = data[pname]
            lines.append(f"    {pdir} {pname} : {_type(p[1])}")
    lines.append("")
    for wname in m["wire"]:
        w = data[wname]
        lines.append(f"    wire {wname} : {_type(w[1])}")
    for rname in m["register"]:
        r = data[rname]
        lines.append(_register(rname, r))
    for iname in m["instance"]:
        i = data[iname]
        cn, mn = i[1][1:3]
        if cn == "mem":
            mm = db["circuits"][cn][mn]
            data = mm["data"]
            attr = {k: data[k][1] for k in mm["attribute"]}
            _memory(iname, attr, lines)
            continue
        lines.append(f"    inst {iname} of {mn}")
    lines.append("")
    _statements(m["code"], lines)
    lines.append("")


def _circuit(name: str, db: DB, lines: list[str]) -> None:
    if name == "mem":
        return
    lines.append(f"circuit {name} :")
    modules = db["circuits"][name]
    for mname in modules:
        _module(name, mname, db, lines)


def firrtl(
    *circuits: str,
    db: Optional[DB] = None,
    name: Optional[str] = None,
    odir: str = ".",
) -> None:
    """
    Generate FIRRTL code for given database and circuits.
    Generate FIRRTL for all circuits if none is specified.
    Use default database if none is specified.
    """
    lines = [_preamble()]
    db = db or default
    circuits = circuits or db["circuits"].keys()
    name = name or circuits[0]
    for circ in circuits:
        _circuit(circ, db, lines)
    with chdir(odir):
        with open(f"{name}.fir", "w") as fh:
            fh.write("\n".join(lines))


def verilog(
    *circuits: str,
    db: Optional[DB] = None,
    name: Optional[str] = None,
    odir: str = ".",
) -> None:
    """
    Generate FIRRTL, and then run firtool to convert it to Verilog
    """
    db = db or default
    circuits = circuits or list(db["circuits"].keys())
    name = name or circuits[0]
    firrtl(*circuits, db=db, name=name, odir=odir)
    with chdir(odir):
        firtool = os.environ.get("FIRTOOL") or "firtool"
        args = [firtool, "--verilog", f"-o={name}.v", f"{name}.fir"]
        r = run(args)
        if r.returncode != 0:
            raise RuntimeError("firtool returned non-zero exit code")
