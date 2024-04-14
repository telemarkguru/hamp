"""
Database
Stores module data
"""

import re
from typing import Union, TypedDict, Optional

TL = tuple
DB = dict[str, dict]
VAL = Union[str, tuple, int]
VAR = Union[str, tuple]
VARS = dict[str, tuple]
DATA = dict[str, TL]
NL = list[str]
ATTR = dict[str, Union[str, int, dict, list]]


class MODULE(TypedDict):
    input: list[str]
    output: list[str]
    wire: list[str]
    register: list[str]
    instance: list[str]
    attribute: list[str]
    data: dict[str, tuple]
    code: list[tuple]


default: DB = {"circuits": {}}


def create() -> DB:
    """Create empty DB"""
    return {"circuits": {}}


def create_module(db: DB, circuit: str, module: str) -> MODULE:
    """Create empty module, add to DB and return it"""
    circ = db["circuits"].setdefault(circuit, {})
    if module in circ:
        raise NameError(f"Module {circuit}::{module} already defined")
    m: MODULE
    circ[module] = m = {
        "input": [],
        "output": [],
        "wire": [],
        "register": [],
        "instance": [],
        "attribute": [],
        "data": {},
        "code": [],
    }
    return m


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
    data = items["data"]
    data_cnt = 0
    for m in items.items():
        match m:
            case ("data", dict(_)):
                pass
            case ("input", list(ports)):
                _validate_data(name, "input", ports, data, vars)
                data_cnt += len(ports)
            case ("output", list(ports)):
                _validate_data(name, "output", ports, data, vars)
                data_cnt += len(ports)
            case ("wire", list(wires)):
                _validate_data(name, "wire", wires, data, vars)
                data_cnt += len(wires)
            case ("register", list(registers)):
                _validate_registers(name, registers, data, vars)
                data_cnt += len(registers)
            case ("instance", list(instances)):
                _validate_instances(name, instances, data, vars, db)
                data_cnt += len(instances)
            case ("code", list(statements)):
                _validate_code(name, statements, vars)
            case ("attribute", list(attributes)):
                _validate_module_attributes(name, attributes, data)
                data_cnt += len(attributes)
            case _:
                raise ValueError(f"Malformed item in module {name}: {m}")
    if data_cnt != len(data):
        raise ValueError(
            f"Malformed data section in module {name}: {data_cnt} {len(data)}"
        )


def _validate_module_attributes(name, attributes, data) -> None:
    for aname in attributes:
        _validate_name(aname)
        a = data[aname]
        match a:
            case ("attribute", value):
                _validate_attribute_value(value)
            case _:
                raise ValueError(
                    f"Malformed attribute entry in module {name}: {a}"
                )


def _validate_attributes(*attributes: ATTR) -> None:
    if not attributes:
        return
    if len(attributes) > 1:
        raise ValueError(f"Surplus attribute data: {list(attributes[1:])}")
    for k, v in attributes[0].items():
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


def _validate_data(
    name: str, kind: str, names: NL, data: DATA, vars: VARS
) -> None:
    for pname in names:
        _validate_name(pname)
        p = data[pname]
        match p:
            case (str(k), type, *attributes) if k == kind:
                _validate_type(type)
                _validate_attributes(*attributes)
                vars[pname] = (type, kind, attributes or {})
            case _:
                raise ValueError(
                    f"Malformed {kind} entry in module {name}: {p}"
                )


_clk_t = ("clock", 1)
_rst_types = (("reset", 1), ("async_reset", 1), ("uint", 1))


def _validate_registers(
    name: str, registers: NL, data: DATA, vars: VARS
) -> None:
    for rname in registers:
        _validate_name(rname)
        r = data[rname]
        match r:
            case ("register", type, str(clk), 0, *attributes):
                _validate_type(type)
                _validate_var(_clk_t, clk, vars)
                _validate_attributes(*attributes)
                vars[rname] = (type, "register", attributes or {}, clk, 0)
            case ("register", type, str(clk), (str(rst), value), *attributes):
                _validate_type(type)
                _validate_var(_clk_t, clk, vars)
                if rst not in vars:
                    raise ValueError(
                        f"Reset signal {rst} not defined in module {name}"
                    )
                for rst_type in _rst_types:
                    try:
                        _validate_var(rst_type, rst, vars)
                        break
                    except ValueError:
                        pass
                else:
                    raise ValueError(
                        f"Bad register reset type: {vars[rst][0]}"
                    )
                _validate_value(type, value, vars)
                _validate_attributes(*attributes)
                vars[rname] = (
                    type,
                    "register",
                    attributes or {},
                    clk,
                    (rst, value),
                )
            case _:
                raise ValueError(
                    f"Malformed register entry in module {name}: {r}"
                )


def _portmap(module):
    return {
        **{n: (module["data"][n][1], "input") for n in module["input"]},
        **{n: (module["data"][n][1], "output") for n in module["output"]},
    }


def _validate_instances(
    name: str, instances: NL, data: DATA, vars: VARS, db: DB
) -> None:
    for iname in instances:
        _validate_name(iname)
        i = data[iname]
        match i:
            case ("instance", ("instance", str(cn), str(mn)), *attributes):
                _validate_attributes(*attributes)
                try:
                    m = db["circuits"][cn][mn]
                except KeyError:
                    raise ValueError(f"No module named {cn}::{mn} found")
                vars[iname] = ("instance", cn, mn, _portmap(m))
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
                _validate_attributes(*attributes)
            case ("when", (("uint", 1), val), stmnts, *attributes):
                _validate_value(("uint", 1), val, vars)
                _validate_code(name, stmnts, vars)
                _validate_attributes(*attributes)
            case ("else-when", (("uint", 1), val), stmnts, *attributes):
                _validate_value(("uint", 1), val, vars)
                _validate_code(name, stmnts, vars)
                _validate_attributes(*attributes)
            case ("else", stmnts, *attributes):
                _validate_code(name, stmnts, vars)
                _validate_attributes(*attributes)
            case ("printf", str(clk), (("uint", 1), en), str(fstr), *args):
                _validate_fmt("printf", clk, en, fstr, args, None, vars)
            case (
                "assertf",
                str(clk),
                (("uint", 1), pred),
                (("uint", 1), en),
                str(fstr),
                *args,
            ):
                _validate_fmt("assertf", clk, en, fstr, args, pred, vars)
            case (
                "coverf",
                str(clk),
                (("uint", 1), pred),
                (("uint", 1), en),
                str(fstr),
            ):
                _validate_fmt("coverf", clk, en, fstr, [], pred, vars)
            case _:
                raise ValueError(
                    f"Malformed statement in module {name}: {statement}"
                )


_arg_ph = re.compile(r"%[bdx]")


def _validate_fmt(
    kind: str,
    clk: str,
    en: tuple,
    fstr: str,
    args,
    pred: Optional[tuple],
    vars: VARS,
) -> None:
    _validate_var(("clock", 1), clk, vars)
    _validate_value(("uint", 1), en, vars)
    if pred:
        _validate_value(("uint", 1), pred, vars)
    for a in args:
        match a:
            case type, value:
                _validate_value(type, value, vars)
            case _:
                raise ValueError(f"Malformed expression: {a}")
        if type[0] not in ("uint", "sint", "clock", "async_reset", "reset"):
            raise ValueError(f"Not ground type: {type}")
    ph = _arg_ph.findall(fstr)
    if len(ph) != len(args):
        raise ValueError(
            f"Placeholders vs arguments mismatch {len(ph)} != {len(args)}"
        )


def _validate_type(type: tuple) -> None:
    match type:
        case ("uint", int(bits)):
            if not (bits >= 0):
                raise ValueError(f"Bad uint size: {bits}")
        case ("sint", int(bits)):
            if not (bits >= 0):
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
        case (".", (("instance", str(cn), str(mn)), str(iname)), str(port)):
            _validate_instance_port(type, cn, mn, iname, port, vars)
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
            if len(x) > type[1]:
                raise ValueError(
                    f"Too many array values: {len(x)} > {type[1]}"
                )
            for v in x:
                _validate_value(type[2], v, vars)
        case _:
            raise ValueError(f"Malformed value {value} of type {type}")


def _validate_instance_port(
    type: tuple, cn: str, mn: str, name: str, port: str, vars: VARS
) -> None:
    if name not in vars or vars[name][0] != "instance":
        raise ValueError(f"Module {vars['module']} has no instance {name}")
    cname, mname, portmap = vars[name][1:5]
    if cname != cn or mname != mn:
        raise ValueError(
            f"Inconsistent module names {cn}::{mn} vs {cname}::{mname}"
        )
    if port not in portmap:
        raise ValueError(f"Module {cname}::{mname} has no port {port}")
    ptype, pdir = portmap[port]
    if type != ptype:
        raise ValueError(
            f"Inconsistent {pdir} port type {type} != {ptype} "
            f"for {cname}::{mname}.{port}"
        )
