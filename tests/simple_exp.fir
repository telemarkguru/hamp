FIRRTL version 1.1.0
circuit test :

  module test :
    input x : UInt<1>
    input en : UInt<1>
    output y : UInt<4>

    wire w : UInt<3>

    when en :
        w <= add(x, UInt<1>(1))
    else :
        w <= sub(x, UInt<1>(1))
    y <= add(w, UInt<1>(1))
