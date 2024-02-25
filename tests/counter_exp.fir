FIRRTL version 1.1.0
circuit test :

  module test :
    input clk : Clock
    input rst : AsyncReset
    input en : UInt<1>
    output out : UInt<10>

    reg cnt : UInt<10>, clk with: (reset => (rst, UInt<10>(0)))

    when en :
        cnt <= bits(add(cnt, UInt<2>(3)), 9, 0)
    out <= cnt
