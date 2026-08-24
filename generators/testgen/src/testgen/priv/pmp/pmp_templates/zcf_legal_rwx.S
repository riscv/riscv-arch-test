.macro VERIFICATION_RWX ADDRESS TEST_CASE

    li    x15, 0x3f800000    // bit pattern for 1.0f (IEEE-754 single)
    fmv.w.x f8, x15          // move 32-bit integer bits into float reg f8
    // Store Access Check
    LA(x8, \ADDRESS)                                         // Address to be verified
    \TEST_CASE\()_1:
    c.fsw f8, 0(x8)
    c.nop
    c.nop
    c.nop
    c.nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)

    \TEST_CASE\()_2:
    c.flw f8, 0(x8)
    c.nop
    c.nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)

    mv t0, sp
    addi sp, x8, 0
    c.fswsp f8, 0(sp)
    c.nop
    c.nop
    c.nop
    c.nop
    c.flwsp f8, 0(sp)
    c.nop
    c.nop
    mv sp, t0

.endm
