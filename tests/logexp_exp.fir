FIRRTL version 1.1.0
circuit logexp :

  module logexp :
    input a : UInt<3>
    input b : SInt<4>
    input c : UInt<1>
    output x : UInt<1>
    output y : UInt<3>

    

    x <= and(orr(a), and(orr(b), c))
    y <= UInt(0)
    when not(orr(a)) :
        y <= UInt(1)
    else when or(orr(a), c) :
        y <= UInt(2)
    else when orr(b) :
        y <= UInt(3)
