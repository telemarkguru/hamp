FIRRTL version 4.2.0
circuit print :

  public module print :
    input clk : Clock
    input en : UInt<1>
    input pred : UInt<1>


    assert(clk, pred UInt<1>(1), "hello world1")
    assert(clk, pred en, "hello world2 %b", en)
    assert(clk, pred UInt<1>(1), "hello world3")
    assert(clk, pred en, "hello world4")
