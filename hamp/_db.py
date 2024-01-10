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
                ("register-name", TYPE, RESET_SIGNAL, VALUE, ATTRIBUTES*),
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
        ("field-name", TYPE),
        ...
    )
WIDHT: -1 or non-zero positive integer.  -1 means unsized.
SIZE: non-zero positive integer

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


def validate(db):
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
                        _validate_circuit(name, modules)
                    case _:
                        raise ValueError(f"Malformed circuit entry: {c}")
        case _:
            raise ValueError("Malformed database, expecting only circuits key")


def _validate_circuit(name, db):
    """Validate circuit entry"""
    for m in db.items():
        match m:
            case (str(name), dict(items)):
                _validate_module(name, items)
            case _:
                raise ValueError(
                    f"Malformed module entry in circuit {name}: {m}"
                )


def _validate_module(name, db):
    """Validate module entry"""

    vars = {"module": name}
    for m in db.items():
        match m:
            case ("ports", list(ports)):
                _validate_ports(name, ports, vars)
            case ("wires", list(wires)):
                _validate_wires(name, wires, vars)
            case ("registers", list(registers)):
                _validate_registers(name, registers, vars)
            case ("code", list(statements)):
                _validate_code(name, statements, vars)
            case _:
                raise ValueError(f"Malformed item in module {name}: {m}")


def _validate_annotations(annotations):
    # TODO: add validation
    pass


def _validate_ports(name, ports, vars):
    for p in ports:
        match p:
            case (str(pname), "input", type, *annotations):
                _validate_type(type)
                _validate_annotations(annotations)
                vars[pname] = (type, "input", annotations)
            case (str(pname), "output", type, *annotations):
                _validate_type(type)
                _validate_annotations(annotations)
                vars[pname] = (type, "output", annotations)
            case _:
                raise ValueError(f"Malformed port entry in module {name}: {p}")


def _validate_wires(name, wires, vars):
    for w in wires:
        match w:
            case (str(wname), type, *annotations):
                _validate_type(type)
                _validate_annotations(annotations)
                vars[wname] = (type, "wire", annotations)
            case _:
                raise ValueError(f"Malformed wire entry in module {name}: {w}")


def _validate_registers(name, registers, vars):
    for r in registers:
        match r:
            case (str(rname), type, reset, value, *annotations):
                _validate_type(type)
                _validate_annotations(annotations)
                vars[rname] = (type, "register", annotations, reset, value)
            case _:
                raise ValueError(
                    f"Malformed register entry in module {name}: {r}"
                )


def _validate_code(name, statements, vars):
    for statement in statements:
        match statement:
            case ("connect", (t1, var), (t2, val), *annotations):
                _validate_type(t1)
                _validate_var(t1, var, vars)
                _validate_value(t2, val, vars)
                _validate_annotations(annotations)
            case ("when", (("uint", 1), val), stmnts, *annotations):
                _validate_value(("uint", 1), val, vars)
                _validate_code(name, stmnts, vars)
                _validate_annotations(annotations)
            case ("else-when", (("uint", 1), val), stmnts, *annotations):
                _validate_value(("uint", 1), val, vars)
                _validate_code(name, stmnts, vars)
                _validate_annotations(annotations)
            case ("else", stmnts, *annotations):
                _validate_code(name, stmnts, vars)
                _validate_annotations(annotations)
            case _:
                raise ValueError(
                    f"Malformed statement in module {name}: {statement}"
                )


def _validate_type(type):
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
                    case (str(_), type):
                        _validate_type(type)
                    case _:
                        raise ValueError(f"Malformed struct field {f}")
        case _:
            raise ValueError(f"Malformed type: {type}")


_name = re.compile(r"^[a-zA-Z_][a-zA-Z_0-9]*$")


def _validate_name(name):
    if not _name.match(name):
        raise ValueError(f"Malformed name: {name}")


def _struct_fields(fields):
    """Return dict of fields"""
    return {x[0]: x[1] for x in fields}


def _validate_var(type, value, vars):
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
        case _:
            raise ValueError(
                f"Malformed variable {value} of type {type}"
            )


def _validate_value(type, value, vars):
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
            if len(x) > type[1]:
                raise ValueError(f"Too many array values: {len(x)} > {type[1]}")
            for v in x:
                _validate_value(type[2], v, vars)
        case _:
            raise ValueError(f"Malformed value {value} of type {type}")
