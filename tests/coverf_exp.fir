FIRRTL version 4.2.0
circuit print :

  public module print :
    input clk : Clock
    input en : UInt<1>
    input pred : UInt<1>


    cover(clk, pred UInt<1>(1), "hello world1")
    cover(clk, pred en, "hello world2")
    cover(clk, pred UInt<1>(1), "hello world3")
    cover(clk, pred en, "hello world4")
