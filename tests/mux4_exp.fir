FIRRTL version 1.1.0
circuit mux :

  module mux :
    input a : {x: UInt<2>, y: SInt<3>}
    input b : {x: UInt<2>, y: SInt<3>}
    input sel : UInt<1>
    output x : {x: UInt<2>, y: SInt<3>}


    when sel :
        x <= b
    else :
        x <= a

circuit mux4 :

  module mux4 :
    input a : {x: UInt<2>, y: SInt<3>}[4]
    input sel : UInt<2>
    output x : {x: UInt<2>, y: SInt<3>}

    inst m1 of mux
    inst m2 of mux
    inst m3 of mux

    m1.a <= a[UInt(0)]
    m1.b <= a[UInt<1>(1)]
    m1.sel <= bits(sel, 0, 0)
    m2.a <= a[UInt<2>(2)]
    m2.b <= a[UInt<2>(3)]
    m2.sel <= bits(sel, 0, 0)
    m3.a <= m1.x
    m3.b <= m2.x
    m3.sel <= bits(sel, 1, 1)
    x <= m3.x
