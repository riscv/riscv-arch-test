#define VALUE         0x00010001

.macro VERIFICATION_RWX ADDRESS TEST_CASE

    LA (x15, \ADDRESS)
    LA(x1, 1f)                            // Store the return Address in x1
    RVTEST_FENCEI                              // sync I-cache: a prior store may have updated this executable region
    \TEST_CASE\()_3:
    c.jalr x15
    c.nop
    c.nop
1:
    c.nop
    c.nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)

    LI(x15, VALUE)                                              // Value to write (VALUE)
    // Store Access Check
    LA(x8, \ADDRESS)                                         // Address to be verified
   \TEST_CASE\()_1:
    c.sw x15, 0(x8)
    c.nop
    c.nop
    c.nop
    c.nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)
    \TEST_CASE\()_2:
    c.lw x15, 0(x8)
    c.nop
    c.nop
    c.nop
    c.nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)

    mv t0, sp
    addi sp, x8, 0

    c.swsp x15, 0(sp)
    c.nop
    c.nop
    c.nop
    c.nop
    c.nop
    c.nop
    c.nop
    c.nop

    c.lwsp x15, 0(sp)
    c.nop
    c.nop
    mv sp, t0

    c.nop
    c.nop
    c.nop
    c.nop
    c.nop
    c.nop
    c.nop

.endm
