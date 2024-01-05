FIRRTL version 1.1.0
circuit ops :

  module ops :
    input a : UInt<8>
    input b : UInt<8>
    input c : SInt<8>
    input d : SInt<8>
    output x : UInt<9>[2]
    output y : SInt<9>[2]
    output z : SInt<9>[2]

    

    x[UInt(0)] <= dshr(a, b)
    x[UInt(1)] <= dshl(a, b)
    y[UInt(0)] <= dshr(c, b)
    y[UInt(1)] <= dshl(c, b)
    z[UInt(0)] <= shl(c, 3)
    z[UInt(1)] <= shr(c, 2)
