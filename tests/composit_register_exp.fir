FIRRTL version 1.1.0
circuit composit_register :

  module composit_register :
    input clk : Clock
    input rst : AsyncReset
    input r : SInt<20>
    input i : SInt<20>
    input en : UInt<1>
    output x : SInt<40>

    reg data : {r: SInt<20>, i: SInt<20>}, clk

    when en :
        data.r <= r
        data.i <= i
    x <= mul(data.r, data.i)
