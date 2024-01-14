FIRRTL version 1.1.0
circuit index :

  module index :
    input a : SInt<8>[4][3]
    input x : UInt<2>
    input y : UInt<2>
    output z : UInt<18>
    input b : SInt<10>


    z <= cat(a[x][y], b)
