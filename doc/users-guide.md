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

m.clk = input(clock)
m.rst = input(async_reset)
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

### Arrays

An array of N elements of a type can be declared as:

    some_type[N]

Arrays can be of constructed of any type (arrays, structs and integers).
An array can be indexed by constants or unsigned integer expressions.

### Structs

Structs are built on top of Python dataclasses, and are declared like so:

```Python
@struct
class Foo:
    a: uint[10]
    b: sint[10]
    c: int

@struct
class Bar:
    foo_array: Foo[3]
    cnt: uint[3]
```

Fields can be both of hardware types and of other types, but only hardware
types are translated to FIRRTL. Field of other types can be used to hold meta
data about the hardware, like sizes.

## Hardware elements

### Modules

A public module is created with:
```Python
m = module("name")
```

A module private to another module is created with:
```Python
m = module("public_module_name::name")
```
A private module can be used by the public module it belongs to as well as by
other private modules belonging to the same public module.

### Ports and wires

Wires and input and output ports are added to a module as so:
```Python
m = module("foo")
m.a = input(uint[1])
m.b = output(uint[1])
m.x = wire(uint[1])
```

The type of a port or wire can be any valid hardware type.

### Registers

Registers are added to a module in a similar fashion as wires and ports:
```Python
m = module("foo")
m.clk = input(clock)
m.rst = input(async_reset)
m.z1 = register(uint[3])
m.z1 = register(uint[3], value=1)
m.z3 = register(uint[3], clock=m.clk, reset=m.rst, value=2)
```
Where:
- z1 is a register without reset. Clock is inferred as the first clock in the
  module
- z2 is a register reset to the value 1. Clock and reset are inferred.
- z3 is a register reset to the value 2. Clock and reset are explicit.

Registers can have any valid hardware type.

### Logical function

The logical function of a module is described using Python code that
generates the logic when executed.  When executing this code, only
some parts of it will generate hardware.  These are:

  - If/elif/else statements with conditions containing ports, registers or
    wires.
  - Assignments to wires, register or output ports.

E.g. a loop is not translated directly, but will result in unrolled RTL code if
the loop contain any of the translated statements above.

### Expressions

Expressions containing ports, registers or wires are translated into
expression trees using operator overloading.  These trees are, if used
in any of the statements listed above, stored and translated.

A consequence of this approach, where expressions are build by executing
code, is that expressions can be built using any valid Python code, like
list comprehensions and sum(). E.g:

```Python
    m.a = wire(uint[10][3])
    m.b = wire(uint[10][3])
    m.x = wire(uint[20])

    @m.code
    def main(m):
        # Calculate dot-product
        m.x = sum(a * b for a, b in zip(m.a, m.b))
```

This expression will be unrolled into an expression corresponding to:

```
    x = a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
```

Also, sub-expressions can be stored in plain Python variables and be
reused in multiple places, very much like a macro:

```Python
   ...
   @m.code
   def main(m):
       a = (m.x + m.y) // 2
       if a > 3 and a < 100:
          ...
```

Intermediate values within an expression are always sized so that bits and
precision are never lost. E.g. an add expression yields a result that has one
more bit than the larger of the two operand.

Bits are only lost explicitly, when assigning to something with a narrower
type, or using bit slicing.

### Operators and functions

The supported operators and functions are mostly based on what is available in
FIRRTL, so for the details on each operators exact semantics, refer to the
FIRRTL specification.

Infix and prefix operators are translated to FIRRTL operations as follows:

| Python operator | FIRRTL operation   |
| --------------- | ------------------ |
| +               | add                |
| -               | sub                |
| *               | mul                |
| //              | div                |
| %               | rem                |
| ==              | eq                 |
| !=              | neq                |
| >               | gt                 |
| >=              | geq                |
| <               | lt                 |
| <=              | leq                |
| >>              | dshr or shr        |
| <<              | dshl or shl        |
| &               | and                |
| \|              | or                 |
| ^               | xor                |
| ~               | not                |
| and             | and  [^1]          |
| or              | or   [^1]          |
| not             | not  [^1]          |
| [h:l]           | bits (if uint/sint)|

[^1]: Each operand is first reduced with a or reduction (orr) if not already of
  type uint[1].

## Meta programming

### Adding logic to existing hierarchy

The way modules are modelled makes it possible to add, remove or modify the
content at any time before FIRRTL code is generated.  Two examples where this
can be useful are:

- Adding DFT ports and logic

- Adding a bus structure for control and status registers (CSRs)

  When describing the hardware is then only necessary to mark any register or
  wire that shall be accessible as a CSR.  Making the CSRs accessible via a bus
  structure can then be done programmatically, and the type of bus used can be
  configurable and something the description of the hardware can be agnostic
  about.
