FIRRTL version 4.2.0
circuit index :

  public module index :
    input a : SInt<8>[4][3]
    input x : UInt<2>
    input y : UInt<2>
    input b : SInt<10>
    output z : UInt<18>


    z <= cat(a[x][y], b)
