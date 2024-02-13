FIRRTL version 1.1.0
circuit memories :

  module memories :
    input clk : Clock
    input addr : UInt<8>
    input we : UInt<1>
    input re : UInt<1>
    input ce : UInt<1>
    input wmode : UInt<1>
    input din : {a: UInt<2>, b: SInt<3>, c: SInt<3>[2]}[2]
    output dout : {a: UInt<2>, b: SInt<3>, c: SInt<3>[2]}[2]

    wire wmask : {a: UInt<1>, b: UInt<1>, c: UInt<1>[2]}
    mem ram :
        data-type => {a: UInt<2>, b: SInt<3>, c: SInt<3>[2]}
        depth => 256
        reader => r1
        writer => w1
        readwriter => rw1
        read-latency => 1
        write-latency => 1
        read-under-write => undefined

    ram.r1.en <= re
    ram.r1.clk <= clk
    ram.r1.addr <= addr
    dout[UInt(0)] <= ram.r1.data
    ram.w1.en <= we
    ram.w1.clk <= clk
    ram.w1.addr <= addr
    ram.w1.data <= din[UInt(0)]
    ram.w1.mask <= wmask
    wmask.a <= UInt<1>(1)
    wmask.b <= UInt<1>(1)
    wmask.c[UInt(0)] <= UInt(1)
    wmask.c[UInt(1)] <= UInt(1)
    ram.rw1.en <= ce
    ram.rw1.clk <= clk
    ram.rw1.addr <= addr
    ram.rw1.wmode <= wmode
    ram.rw1.wdata <= din[UInt(1)]
    ram.rw1.wmask <= wmask
    dout[UInt(1)] <= ram.rw1.rdata
