FIRRTL version 1.1.0
circuit functional :

  module functional :
    input i : UInt<10>[5]
    output o : UInt<14>


    o <= add(add(add(add(add(UInt(0), i[UInt(0)]), i[UInt(1)]), i[UInt(2)]), i[UInt(3)]), i[UInt(4)])
