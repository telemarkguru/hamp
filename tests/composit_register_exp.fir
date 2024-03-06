FIRRTL version 4.2.0
circuit composit_register :

  public module composit_register :
    input clk : Clock
    input rst : AsyncReset
    input r : SInt<20>
    input i : SInt<20>
    input en : UInt<1>
    input idx : UInt<2>
    output x : SInt<40>
    output y : SInt<40>

    wire _K0 : const {r: SInt<20>, i: SInt<20>}[3]

    reg data : {r: SInt<20>, i: SInt<20>}, clk
    regreset data2 : {r: SInt<20>, i: SInt<20>}[3], clk, rst, _K0

    when en :
        data.r <= r
        data.i <= i
        data2[idx].r <= r
        data2[idx].i <= i
    x <= mul(data.r, data.i)
    y <= add(add(add(SInt(0), mul(data2[UInt(0)].r, data2[UInt(0)].i)), mul(data2[UInt<1>(1)].r, data2[UInt<1>(1)].i)), mul(data2[UInt<2>(2)].r, data2[UInt<2>(2)].i))

    connect _K0[0].r, SInt<20>(0)
    connect _K0[0].i, SInt<20>(0)
    connect _K0[1].r, SInt<20>(0)
    connect _K0[1].i, SInt<20>(0)
    connect _K0[2].r, SInt<20>(0)
    connect _K0[2].i, SInt<20>(0)
