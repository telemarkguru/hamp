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
        "input": [*NAME],
        "output": [*NAME],
        "wire": [*NAME],
        "register": [*NAME],
        "instance": [*NAME],
        "attribute": [*NAME],
        "data": {
            NAME: DATAITEM,
            ...
        },
        "code": [*CODE],
    }

DATAITEM:
    ("input", TYPE, ATTRIBUTES?)
    ("output", TYPE, ATTRIBUTES?)
    ("wire", TYPE, ATTRIBUTES?)
    ("register", TYPE, CLOCK, RESET, ATTRIBUTES?)
    ("instance", ("instance", NAME, NAME), ATTRIBUTES?)
    ("attribute", ATTRVAL)

TYPE:
    ("uint", WIDTH)
    ("sint", WIDTH)
    ("array", SIZE, TYPE)
    ("struct", (NAME, TYPE, FLIP), *(NAME, TYPE, FLIP))
    ("clock", 1)
    ("reset", 1)
    ("instance", NAME, NAME)  # circuit-name module-name

WIDTH:
    integer, >= 0

SIZE:
    integer >= 1

FLIP:
    0 or 1

CLOCK:
    NAME  # Must be name of variable of type ("clock", 1)

RESET:
    0             # Means no reset
    (NAME, VALUE) # Must be name of variable of type:
                  # ("reset, 1), ("async_reset", 1) or ("uint", 1)
                  # VALUE must be of same type as register

EXPR:
    (TYPE, VALUE)

VALUE:
    integer
    VAR
    (OP, *(TYPE, VALUE))
    {NAME: VALUE, ...}
    [*VALUE]

VAR:
    NAME
    (".", (("struct" ...), VAR), NAME)
    ("[]", (("array", ...), VAR), VALUE)  # Value must be of type ("uint", *)
    (".", (("instance", ...), NAME), NAME)  # inst-name, port-name

OP:
    "+", "-", ...

CODE:
    ("connect", (TYPE, VAR), (TYPE, VALUE), ATTRIBUTES?)
    ("when", (("uint", 1), VALUE), (*CODE), ATTRIBUTES?)
    ("else-when", (("uint", 1), VALUE), (*CODE), ATTRIBUTES?)
    ("else", (*CODE), ATTRIBUTES?)

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
