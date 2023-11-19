FIRRTL version 1.1.0
circuit ops :

  module ops :
    input a : UInt<8>
    input b : UInt<8>
    input c : SInt<8>
    input d : SInt<8>
    output x : UInt<9>[2]
    output y : SInt<9>[2]

    

    x[0] <= dshr(a, b)
    x[1] <= dshl(a, b)
    y[0] <= dshr(c, b)
    y[1] <= dshl(c, b)
