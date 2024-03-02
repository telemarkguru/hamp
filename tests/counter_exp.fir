FIRRTL version 4.2.0
circuit test :

  public module test :
    input clk : Clock
    input rst : AsyncReset
    input en : UInt<1>
    output out : UInt<10>

    regreset cnt : UInt<10>, clk, rst, UInt<10>(0)

    when en :
        cnt <= bits(add(cnt, UInt<2>(3)), 9, 0)
    out <= cnt
