.macro SET_PMP_ENTRY ADDR_REG, CFG_REG, CFG_BITS
    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI (x6, PMP_MASK)
    and x5, x5, x6
    LI(x6, PMP_REGION_SIZE)
    or x5, x5, x6
    csrw \ADDR_REG, x5
    LI(x4, \CFG_BITS)
    csrw \CFG_REG, x4
.endm
