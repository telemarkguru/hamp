"""
Database
Stores module data

Format:

"circuits": {
    "<name>": {
        "<module-name>": {
            "ports": [
                ("port-name", DIRECTION, TYPE, ATTRIBUTES*),
                ...
            ],
            "wires": [
                ("wire-name", TYPE, ATTRIBUTES*),
                ...
            ],
            "registers": [
                ("register-name", TYPE, CLOCK, RESET, ATTRIBUTES*),
                ...
            ],
            "instances": [
                ("instance-name", "circuit-name", "module-name", ATTRIBUTES*),
                ...
            ],
            "code": [
                STATEMENT,
                ...
            ],
        },
        ...
    },
    ...
}


DIRECTION: "input" or "output"
TYPE:
    ("uint", WIDTH)
    ("sint", WIDTH)
    ("array", SIZE, TYPE)
    ("struct",
        ("field-name", TYPE, FLIP),
        ...
    )
WIDHT: -1 or non-zero positive integer.  -1 means unsized.
SIZE: non-zero positive integer
FLIP: 1 to mark flip, 0 otherwise

CLOCK:
    signal-name

RESET:
    0
    (signal-name, value)

STATEMENT:
    ("connect", VARIABLE, EXPRESSION, ANNOTATION*)
    ("when", EXPRESSION,
        (
            STATEMENT,
            ...,
        ),
        ANNOTATION*
    )
    ("else-when", EXPRESSION,
        (
            STATEMENT,
            ...,
        ),
        ANNOTATION*
    )
    ("else",
        (
            STATEMENT,
            ...,
        ),
        ANNOTATION*
    )

VARIABLE:
    (TYPE, "variable-name")
    (TYPE, (".", VARIABLE, "field-name"))  # VARIABLE must have struct type
    (TYPE, ("[]", VARIABLE, EXPRESSION))  # VARIABLE must have array type
                                          # EXPRESSION must have uint type

EXPRESSION:
    VARIABLE,
    (TYPE, (OP, EXPRESSION, EXPRESIION*))  # EXPRESIION must be uint or sint
                                           # TYPE is uint or sint
    (TYPE, VALUE)

OP:
    "+", "-", ...

VALUE:
    INTEGER,
    [VALUE, ...]  # array value
    {"field-name": VALUE, ...}  # struct value

"""


import re
from typing import Union

DB = dict[str, dict]
VAL = Union[str, tuple, int]
VAR = Union[str, tuple]
VARS = dict[str, tuple]


def validate(db: DB) -> None:
    """Validate that db is a valid modules database"""
    match db:
        case {"circuits": dict(x), **kw}:
            if kw:
                raise ValueError(
                    "Malformed database, expecting only circuits key"
                )
            for c in x.items():
                match c:
                    case (str(name), dict(modules)):
                        _validate_circuit(name, modules, db)
                    case _:
                        raise ValueError(f"Malformed circuit entry: {c}")
        case _:
            raise ValueError("Malformed database, expecting only circuits key")


def _validate_circuit(name: str, modules: DB, db: DB) -> None:
    """Validate circuit entry"""
    for m in modules.items():
        match m:
            case (str(name), dict(items)):
                _validate_module(name, items, db)
            case _:
                raise ValueError(
                    f"Malformed module entry in circuit {name}: {m}"
                )


def _validate_module(name: str, items: DB, db: DB) -> None:
    """Validate module entry"""

    vars = {"module": name}
    for m in items.items():
        match m:
            case ("ports", list(ports)):
                _validate_ports(name, ports, vars)
            case ("wires", list(wires)):
                _validate_wires(name, wires, vars)
            case ("registers", list(registers)):
                _validate_registers(name, registers, vars)
            case ("instances", list(instances)):
                _validate_instances(name, instances, vars, db)
            case ("code", list(statements)):
                _validate_code(name, statements, vars)
            case ("attributes", dict(attributes)):
                _validate_attributes(attributes)
            case _:
                raise ValueError(f"Malformed item in module {name}: {m}")


def _validate_attributes(attributes) -> None:
    if isinstance(attributes, list):
        for x in attributes:
            _validate_attributes(x)
        return
    for k, v in attributes.items():
        _validate_name(k)
        _validate_attribute_value(v)


def _validate_attribute_value(v):
    match v:
        case int(x):
            pass
        case str(x):
            pass
        case float(x):
            pass
        case dict(x):
            for k, v in x.items():
                _validate_name(k)
                _validate_attribute_value(v)
        case list(x):
            for v in x:
                _validate_attribute_value(v)
        case tuple(x):
            for v in x:
                _validate_attribute_value(v)
        case _:
            raise ValueError(f"Malformed attribute value: {v}")


def _validate_ports(name: str, ports: list[tuple], vars: VARS) -> None:
    for p in ports:
        match p:
            case (str(pname), "input", type, *attributes):
                _validate_type(type)
                _validate_attributes(attributes)
                vars[pname] = (type, "input", attributes)
            case (str(pname), "output", type, *attributes):
                _validate_type(type)
                _validate_attributes(attributes)
                vars[pname] = (type, "output", attributes)
            case _:
                raise ValueError(f"Malformed port entry in module {name}: {p}")


def _validate_wires(name: str, wires: list[tuple], vars: VARS) -> None:
    for w in wires:
        match w:
            case (str(wname), type, *attributes):
                _validate_type(type)
                _validate_attributes(attributes)
                vars[wname] = (type, "wire", attributes)
            case _:
                raise ValueError(f"Malformed wire entry in module {name}: {w}")


def _validate_registers(name: str, registers: list[tuple], vars: VARS) -> None:
    for r in registers:
        match r:
            case (str(rname), type, clk, 0, *attributes):
                _validate_type(type)
                _validate_var(("clock", 1), clk, vars)
                _validate_attributes(attributes)
                vars[rname] = (type, "register", attributes, clk, 0)
            case (str(rname), type, clk, (reset, value), *attributes):
                _validate_type(type)
                _validate_var(("clock", 1), clk, vars)
                _validate_attributes(attributes)
                _validate_value(type, value, vars)
                vars[rname] = (
                    type,
                    "register",
                    attributes,
                    clk,
                    (reset, value),
                )
            case _:
                raise ValueError(
                    f"Malformed register entry in module {name}: {r}"
                )


def _validate_instances(
    name: str, instances: list[tuple], vars: VARS, db: DB
) -> None:
    for i in instances:
        match i:
            case (str(iname), str(cname), str(mname), *attributes):
                _validate_attributes(attributes)
                try:
                    m = db["circuits"][cname][mname]
                except KeyError:
                    raise ValueError(f"No module named {cname}::{mname} found")
                portmap = {n: (t, d) for n, d, t, *_ in m["ports"]}
                vars[iname] = ("instance", cname, mname, portmap)
            case _:
                raise ValueError(
                    f"Malformed instance entry in module {name}: {i}"
                )


def _validate_code(name: str, statements: list[tuple], vars: VARS) -> None:
    t1: tuple
    t2: tuple
    val: VAL
    var: VAR
    for statement in statements:
        match statement:
            case ("connect", (t1, var), (t2, val), *attributes):
                _validate_type(t1)
                _validate_var(t1, var, vars)
                _validate_value(t2, val, vars)
                _validate_attributes(attributes)
            case ("when", (("uint", 1), val), stmnts, *attributes):
                _validate_value(("uint", 1), val, vars)
                _validate_code(name, stmnts, vars)
                _validate_attributes(attributes)
            case ("else-when", (("uint", 1), val), stmnts, *attributes):
                _validate_value(("uint", 1), val, vars)
                _validate_code(name, stmnts, vars)
                _validate_attributes(attributes)
            case ("else", stmnts, *attributes):
                _validate_code(name, stmnts, vars)
                _validate_attributes(attributes)
            case _:
                raise ValueError(
                    f"Malformed statement in module {name}: {statement}"
                )


def _validate_type(type: tuple) -> None:
    match type:
        case ("uint", int(bits)):
            if not (bits > 0 or bits == -1):
                raise ValueError(f"Bad uint size: {bits}")
        case ("sint", int(bits)):
            if not (bits > 0 or bits == -1):
                raise ValueError(f"Bad sint size: {bits}")
        case ("array", int(size), type):
            if size < 1:
                raise ValueError(f"Bad array size: {size}")
            _validate_type(type)
        case ("struct", *fields):
            for f in fields:
                match f:
                    case (str(_), type, 0) | (str(_), type, 1):
                        _validate_type(type)
                    case _:
                        raise ValueError(f"Malformed struct field {f}")
        case ("clock", 1):
            pass
        case ("reset", 1):
            pass
        case ("async_reset", 1):
            pass
        case _:
            raise ValueError(f"Malformed type: {type}")


_name = re.compile(r"^[a-zA-Z_][a-zA-Z_0-9]*$")


def _validate_name(name: str) -> None:
    if not _name.match(name):
        raise ValueError(f"Malformed name: {name}")


def _struct_fields(fields: tuple[tuple[str, tuple], ...]) -> dict[str, tuple]:
    """Return dict of fields"""
    return {x[0]: x[1] for x in fields}


def _validate_var(type: tuple, value, vars: VARS) -> None:
    match value:
        case str(x):
            _validate_name(x)
            if x not in vars:
                raise ValueError(
                    f"Module {vars['module']} has no member named {x}"
                )
            vt = vars[x][0]
            if vt != type:
                raise ValueError(f"Inconsistent type {vt} != {type}")
        case (".", (("struct", *f), v), str(field)):
            t = ("struct", *f)
            _validate_type(t)
            if field not in _struct_fields(f):
                raise ValueError(f"Struct {f} has no field {field}")
            _validate_var(t, v, vars)
        case ("[]", (("array", int(size), t), v), (("uint", int(b)), i)):
            at = ("array", size, t)
            _validate_type(at)
            _validate_var(at, v, vars)
            _validate_value(("uint", b), i, vars)
        case (".", "instance", str(iname), str(port)):
            _validate_instance_port(type, iname, port, vars)
        case _:
            raise ValueError(f"Malformed variable {value} of type {type}")


def _validate_value(type: tuple, value, vars: VARS) -> None:
    _validate_type(type)
    tname = type[0]
    is_int = tname in ("uint", "sint")
    match value:
        case int(x) if is_int:
            pass
        case (".", *_) | ("[]", *_) | str(_):
            _validate_var(type, value, vars)
        case (str(_), *args) if is_int:
            # TODO: check op?
            for arg in args:
                match arg:
                    case (("uint", int(s)), v):
                        _validate_value(("uint", s), v, vars)
                    case (("sint", int(s)), v):
                        _validate_value(("sint", s), v, vars)
                    case _:
                        raise ValueError(
                            f"Malformed expression: {arg} in {value}"
                        )
        case dict(x) if tname == "struct":
            fields = _struct_fields(type[1:])
            for k, v in x.items():
                if k not in fields:
                    raise ValueError(f"Struct {type} has no field {k}")
                _validate_value(fields[k], v, vars)
        case list(x) if tname == "array":
            if len(x) != type[1]:
                raise ValueError(
                    f"Wrong number of array values: {len(x)} != {type[1]}"
                )
            for v in x:
                _validate_value(type[2], v, vars)
        case _:
            raise ValueError(f"Malformed value {value} of type {type}")


def _validate_instance_port(
    type: tuple, name: str, port: str, vars: VARS
) -> None:
    if name not in vars or vars[name][0] != "instance":
        raise ValueError(f"Module {vars['module']} has no instance {name}")
    cname, mname, portmap = vars[name][1:5]
    if port not in portmap:
        raise ValueError(f"Module {cname}::{mname} has no port {port}")
    ptype, pdir = portmap[port]
    if type != ptype:
        raise ValueError(
            f"Inconsistent {pdir} port type {type} != {ptype} "
            f"for {cname}::{mname}.{port}"
        )
