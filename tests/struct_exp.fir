FIRRTL version 1.1.0
circuit struct :

  module struct :
    input clk : Clock
    input din : {valid: UInt<1>, flip ready: UInt<1>, data: {x: UInt<12>, y: SInt<12>}}
    output dout : {valid: UInt<1>, flip ready: UInt<1>, data: {x: UInt<12>, y: SInt<12>}}

    reg x : {x: UInt<12>, y: SInt<12>}, clk

    x <= din.data
    dout.data <= x
    dout.valid <= din.valid
    din.ready <= dout.ready
