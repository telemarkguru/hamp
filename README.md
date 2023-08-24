# hamp
Hardware description meta programming in Python

A library with tools for generating and manipulating hardware descriptions at
Register Transfer Level (RTL).  The output is mainly FIRRTL
(https://github.com/chipsalliance/firrtl-spec/blob/main/spec.md) as this is
an excellent format for describing hardware at a fundamental RTL level
and it has great tools for e.g. generating Verilog.

The intention is to enable creating of RTL programmatically using
meta-programming in Python.  This includes:

- Creating RTL modules
- Populating RTL modules with
    - Input ports
    - Output ports
    - Wires/signals
    - Registers
    - Instantiations of other modules
    - Behavioral code and connections
    - Meta-data about the module or its content

- Manipulate module hierarchies
- Manipulate modules:
    - Cloning a module and give it a new name
    - Add and remove ports, signals, code, instances, meta-data etc.

- Define RTL composite types (structs).


A simple example:
```Python
from hamp import module, input, output, wire, register, uint

u1 = uint[1]

def create_fifo(size, data_type):

    ptr_type = uint[(size-1).bit_length()]
    cnt_type = uint[size.bit_length()]

    m = module(f"fifo_{size}")
    m.in_valid = input(u1)
    m.in_ready = output(u1)
    m.in_data = input(data_type)
    m.out_valid = output(u1)
    m.out_ready = input(u1)
    m.out_data = output(data_type)

    m.data = register(data_type[size])
    m.iptr = register(ptr_type, reset_value=0)
    m.optr = register(ptr_type, reset_value=0)
    m.cnt = register(cnt_type, reset_value=0)

    m.istb = wire(u1)
    m.ostb = wire(u1)

    @m.code
    def fifo(mb):
        mb.in_ready = mb.cnt < size
        mb.out_valid = mb.cnt > 0
        mb.istb = mb.in_valid and mb.in_ready
        mb.ostb = mb.out_valid and mb.out_ready
        if mb.istb:
            mb.data[iptr] = mb.in_data
            mb.iptr = (mb.iptr + 1) % size
        if mb.ostb:
            mb.optr = (mb.optr + 1) % size
        if mb.istb and not mb.ostb:
            mb.cnt = mb.cnt + 1
        elif mb.ostb and not mb.istb:
            mb.cnt = mb.cnt - 1

    return m


fifo1 = create_fifo(42, uint[10])

# Add DFT ports:
fifo1.dft = input(dft_type)

```

## Data types

```Python
from hamp import struct
```

## Function calls

```Python
from hamp import module, input, output, uint

dt = uint[32]
stages = 10

m = module("module)
m.din = input(dt)
m.dout = output(dt)
m.data = wire(dt[stages])

@m.function
def stage(mb, idx: int, value: int):
    mb.data[idx] = mb.data[idx-1] + value

@m.code
def main(mb):
    mb.data[0] = m.din
    for i in range(mb, 1, size):
        mb.stage(i, -42)
    mb.dout = m.data[size-1]

```
