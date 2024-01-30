# HAMP Users Guide

HAMP is a Python library for generating RTL.

The hardware structure and functionality is built using a Python API,
which is used to generate an [intermediate format](data-format.md)
describing the RTL.  The intermediate format can then converted into
FIRRTL, which can be converted to Verilog using **firtool**
(see https://github.com/chipsalliance/firrtl-spec/blob/main/spec.md).

Let's start with a very simple example:

```Python
from hamp import (
    module,
    input,
    output,
    register,
    uint,
    clock,
    async_reset,
    build,
    generate_firrtl
)

m = module("counter")

m.clk = input(clock())
m.rst = input(async_reset())
m.cnt = register(uint[8], value=0)
m.zero = output(uint[1])
m.en = input(uint[1])

@m.code
def counter(m):
    if m.en:
        m.cnt += 1
    m.zero = (m.zero == 0)

# Convert to intermediate format:
db = {}
build(m, db)

# Generate FIRRTL:
with open("counter.fir", "w") as fh:
    fh.write(generate_firrtl(db))
```

## Hardware data types

### Integers

Signed and unsigned integers of arbitrary size are supported:

- **uint[N]** denotes an N bit wide unsigned integer.
- **sint[N]** denotes an N bit wide signed integer.

In both cases, N must of course be a constant.

### Arrays

An array of N elements of a type can be declared:

    some_type[N]

Arrays can be of constructed of any type (arrays, structs and integers).

### Structs

## Hardware elements

### Modules

### Ports

### Registers

### Logical function

The logical function of a module is described using Python code that
generates the logic when executed.  When executing this code, only
some parts of it will generate hardware.  These are:

  - If/elif/else statements with conditions containing ports, registers or
    wires.
  - Assignments to wires, register or output ports.

E.g. a loop is not translated directly, but will result in unrolled RTL code if
the loop contain any of the translated statements.

Expressions containing ports, registers or wires are translated using operator
overloading.




## Meta programming

### Adding logic to existing hierarchy

