FIRRTL version 4.2.0
circuit functional :

  public module functional :
    input i : UInt<10>[5]
    output o : UInt<14>
    output c : UInt<4>


    o <= add(add(add(add(add(UInt(0), i[UInt(0)]), i[UInt<1>(1)]), i[UInt<2>(2)]), i[UInt<2>(3)]), i[UInt<3>(4)])
    c <= add(add(add(add(add(add(add(add(add(add(UInt(0), bits(i[UInt(0)], 0, 0)), bits(i[UInt(0)], 1, 1)), bits(i[UInt(0)], 2, 2)), bits(i[UInt(0)], 3, 3)), bits(i[UInt(0)], 4, 4)), bits(i[UInt(0)], 5, 5)), bits(i[UInt(0)], 6, 6)), bits(i[UInt(0)], 7, 7)), bits(i[UInt(0)], 8, 8)), bits(i[UInt(0)], 9, 9))
