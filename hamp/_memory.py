"""
Memory instance creation
"""

from ._hwtypes import _HWType, uint, u1, clock, _Int, _Struct, _Array
from ._module import _Instance, module, input, attribute
from ._struct import struct, flip, members


def wmask_type(type):
    """Create mask type"""
    if isinstance(type, _Int):
        return u1
    if isinstance(type, _Struct):

        class _MaskStruct:
            pass

        for name, type in members(type):
            _MaskStruct.__annotations__[name] = wmask_type(type)
        return struct(_MaskStruct)
    if isinstance(type, _Array):
        return _Array(wmask_type(type.type), type.size)
    assert False, f"type={type}"  # pragma: no cover


# mypy: ignore-errors


def memory(
    type: _HWType,
    depth: int,
    readers: list[str] = [],
    writers: list[str] = [],
    readwriters: list[str] = [],
    read_latency: int = 1,
    write_latency: int = 1,
    write_mask: bool = True,
) -> _Instance:
    """Create memory instance"""

    addr_bits = (depth - 1).bit_length()
    addr_t = uint[addr_bits]
    clock_t = clock()
    mtype = wmask_type(type)

    m = module("")
    m._ismem = attribute(1)

    if readers:

        @struct
        class Reader:
            addr: addr_t
            en: u1
            clk: clock_t
            data: flip(type)

        for r in readers:
            setattr(m, r, input(Reader))

    if writers:

        @struct
        class Writer:
            addr: addr_t
            en: u1
            clk: clock_t
            data: type
            if write_mask:
                mask: mtype

        for w in writers:
            setattr(m, w, input(Writer))

    if readwriters:

        @struct
        class ReadWriter:
            addr: addr_t
            en: u1
            clk: clock_t
            rdata: flip(type)
            wmode: u1
            wdata: type
            if write_mask:
                wmask: mtype

        for rw in readwriters:
            setattr(m, rw, input(ReadWriter))

    return m()
