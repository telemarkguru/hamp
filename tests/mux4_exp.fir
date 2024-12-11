FIRRTL version 4.2.0
circuit mux :

  public module mux :
    input a : {x: UInt<2>, y: SInt<3>}
    input b : {x: UInt<2>, y: SInt<3>}
    input sel : UInt<1>
    output x : {x: UInt<2>, y: SInt<3>}


    when sel :
        connect x, b
    else :
        connect x, a

circuit mux4 :

  public module mux4 :
    input a : {x: UInt<2>, y: SInt<3>}[4]
    input sel : UInt<2>
    output x : {x: UInt<2>, y: SInt<3>}

    inst m1 of mux
    inst m2 of mux
    inst m3 of mux

    connect m1.a, a[UInt(0)]
    connect m1.b, a[UInt<1>(1)]
    connect m1.sel, bits(sel, 0, 0)
    connect m2.a, a[UInt<2>(2)]
    connect m2.b, a[UInt<2>(3)]
    connect m2.sel, bits(sel, 0, 0)
    connect m3.a, m1.x
    connect m3.b, m2.x
    connect m3.sel, bits(sel, 1, 1)
    connect x, m3.x
