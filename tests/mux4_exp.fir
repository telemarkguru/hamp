FIRRTL version 1.1.0
circuit mux4 :

  module mux4 :
    input a : {x: UInt<2>, y: SInt<3>}[4]
    output x : {x: UInt<2>, y: SInt<3>}
    input sel : UInt<2>

    inst m1 of mux
    inst m2 of mux
    inst m3 of mux

    m1.a <= a[0]
    m1.b <= a[1]
    m1.sel <= bits(sel, 0, 0)
    m2.a <= a[2]
    m2.b <= a[3]
    m2.sel <= bits(sel, 0, 0)
    m3.a <= m1.x
    m3.b <= m2.x
    m3.sel <= bits(sel, 1, 1)
    x <= m3.x


  module mux :
    input a : {x: UInt<2>, y: SInt<3>}
    input b : {x: UInt<2>, y: SInt<3>}
    output x : {x: UInt<2>, y: SInt<3>}
    input sel : UInt<1>

    

    when sel :
        x <= b
    else :
        x <= a
