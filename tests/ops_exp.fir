FIRRTL version 4.2.0
circuit ops :

  public module ops :
    input a : UInt<8>
    input b : UInt<8>
    input c : SInt<8>
    input d : SInt<8>
    output x : UInt<9>[2]
    output y : SInt<263>[2]
    output z : SInt<11>[2]


    x[UInt(0)] <= dshr(a, b)
    x[UInt<1>(1)] <= bits(dshl(a, b), 8, 0)
    y[UInt(0)] <= dshr(c, b)
    y[UInt<1>(1)] <= dshl(c, b)
    z[UInt(0)] <= shl(c, 3)
    z[UInt<1>(1)] <= shr(c, 2)
