# Intermediate data format


## Top level
```
DATABASE:
    {
        "circuits": {
            NAME: MODULES,
            ...
        }
    }

# The circuit name "mem" is reserved for memories


NAME:
    "[A-Za-z_][A-Za-z0-9_]*"

MODULES:
    {
        NAME: MODULE,
        ...
    }

MODULE:
    {
        "ports": [*PORT]
        "wires": [*WIRE]
        "registers": [*REGISTER]
        "instances": [*INSTANCE],
        "code": [*CODE],
        "attributes": ATTRIBUTES,
    }

PORT:
    (NAME, DIRECTION, TYPE, *ATTRIBUTES)

DIRECTION:
    "input"
    "output"

TYPE:
    ("uint", WIDTH)
    ("sint", WIDTH)
    ("array", SIZE, TYPE)
    ("struct", (NAME, TYPE, FLIP), *(NAME, TYPE, FLIP))
    ("clock", 1)
    ("reset", 1)

WIDTH:
    integer, -1 or >= 1

SIZE:
    integer >= 1

FLIP:
    0 or 1

WIRE:
    (NAME, TYPE, *ATTRIBUTES)

REGISTER:
    (NAME, TYPE, CLOCK, RESET, *ATTRIBUTES)

CLOCK:
    VAR or type ("clock", 1)

RESET:
    0
    (VAR, VALUE)  # VAR is of type ("reset", 1), VALUE of reg TYPE

VALUE:
    integer
    VAR
    (OP, *(TYPE, VALUE))
    {NAME: VALUE, ...}
    [*VALUE]

VAR:
    NAME
    (".", (("struct" ...), VAR) NAME)
    ("[]", (("array", ...), VAR) VALUE)  # Value must be of type ("uint", *)
    (".", "instance", NAME, NAME)  # instance-name, port-name

OP:
    "+", "-", ...

INSTANCE:
    (NAME, NAME, NAME, *ATTRIBUTES)
    # instance-name, circuit-name, module-name

CODE:
    ("connect", (TYPE, VAR), (TYPE, VALUE))
    ("when", (("uint", 1), VALUE), (*CODE), *ATTRIBUTES)
    ("else-when", (("uint", 1), VALUE), (*CODE), *ATTRIBUTES)
    ("else", (*CODE), *ATTRIBUTES)

ATTRIBUTES:
    {}
    {
        NAME: ATTRVAL
        ...
    }

ATTRVAL:
    integer
    string
    [*ATTRVAL]
    {
        string: ATTRVAL
        ...
    }

```
