
  .if \level == LEVEL1
    // Adjust offset of VA to point to test region
    LI(  a5, (\VA>>22)<<22)
    LI(  a0, \PA)
    slli a0, a0, 10
    srli a0, a0, 10
    add  a5, a5, a0
  .else
    LI(  a5, \VA)
  .endif
