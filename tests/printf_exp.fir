FIRRTL version 4.2.0
circuit print :

  public module print :
    input clk : Clock
    input en : UInt<1>


    printf(clk, UInt<1>(1), "hello world1")
    printf(clk, en, "hello world2 %b", en)
    printf(clk, UInt<1>(1), "hello world3")
    printf(clk, en, "hello world4")
