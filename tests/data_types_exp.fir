FIRRTL version 4.2.0
circuit data_types :

  public module data_types :
    input a : {r: SInt<32>, i: SInt<32>}
    input c : {x: {r: SInt<32>, i: SInt<32>}, y: {r: SInt<32>, i: SInt<32>}, z: {r: SInt<32>, i: SInt<32>}[4], g: {r: SInt<32>, i: SInt<32>}[4][2]}
    input c2 : {x: {r: SInt<32>, i: SInt<32>}, y: {r: SInt<32>, i: SInt<32>}, z: {r: SInt<32>, i: SInt<32>}[4], g: {r: SInt<32>, i: SInt<32>}[4][2]}[2]
    input r : {a: {x: {r: SInt<32>, i: SInt<32>}, y: {r: SInt<32>, i: SInt<32>}, z: {r: SInt<32>, i: SInt<32>}[4], g: {r: SInt<32>, i: SInt<32>}[4][2]}, b: {x: {r: SInt<32>, i: SInt<32>}, y: {r: SInt<32>, i: SInt<32>}, z: {r: SInt<32>, i: SInt<32>}[4], g: {r: SInt<32>, i: SInt<32>}[4][2]}, c: UInt<2>}
    input r3 : {a: {x: {r: SInt<32>, i: SInt<32>}, y: {r: SInt<32>, i: SInt<32>}, z: {r: SInt<32>, i: SInt<32>}[4], g: {r: SInt<32>, i: SInt<32>}[4][2]}, b: {x: {r: SInt<32>, i: SInt<32>}, y: {r: SInt<32>, i: SInt<32>}, z: {r: SInt<32>, i: SInt<32>}[4], g: {r: SInt<32>, i: SInt<32>}[4][2]}, c: UInt<2>}[3]
    input zsel : UInt<2>
    input gsel : UInt<1>
    input rsel : UInt<1>
    output z : {r: SInt<32>, i: SInt<32>}[3]


    z[UInt(0)] <= r3[rsel].a.g[gsel][zsel]
    z[UInt<1>(1)] <= r.b.z[zsel]
    z[UInt<2>(2)] <= c2[rsel].x
