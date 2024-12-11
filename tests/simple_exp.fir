FIRRTL version 4.2.0
circuit test :

  public module test :
    input x : UInt<1>
    input en : UInt<1>
    output y : UInt<4>

    wire w : UInt<3>

    when en :
        connect w, add(x, UInt<1>(1))
    else :
        connect w, sub(x, UInt<1>(1))
    connect y, add(w, UInt<1>(1))
