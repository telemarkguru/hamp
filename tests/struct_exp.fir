FIRRTL version 4.2.0
circuit struct :

  public module struct :
    input clk : Clock
    input din : {valid: UInt<1>, flip ready: UInt<1>, data: {x: UInt<12>, y: SInt<12>[3]}, data2: {x: UInt<12>, y: SInt<12>[3]}[3]}
    input sel : UInt<2>
    output dout : {valid: UInt<1>, flip ready: UInt<1>, data: {x: UInt<12>, y: SInt<12>[3]}, data2: {x: UInt<12>, y: SInt<12>[3]}[3]}

    reg x : {x: UInt<12>, y: SInt<12>[3]}, clk
    reg y : {x: UInt<12>, y: SInt<12>[3]}[3], clk

    x <= din.data
    y[sel] <= din.data
    dout.data <= x
    dout.data2 <= y
    dout.valid <= din.valid
    din.ready <= dout.ready
