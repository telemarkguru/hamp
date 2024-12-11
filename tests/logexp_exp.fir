FIRRTL version 4.2.0
circuit logexp :

  public module logexp :
    input a : UInt<3>
    input b : SInt<4>
    input c : UInt<1>
    output x : UInt<1>
    output y : UInt<3>


    connect x, and(orr(a), and(orr(b), c))
    connect y, UInt<3>(0)
    when not(orr(a)) :
        connect y, UInt<3>(1)
    else when or(orr(a), c) :
        connect y, UInt<3>(2)
    else when orr(b) :
        connect y, UInt<3>(3)
