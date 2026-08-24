.macro VERIFICATION_RWX ADDRESS TEST_CASE

    // Execution Access Check
    LA (a4, \ADDRESS)
    LA(x1, 1f)                          // Store the return Address in x1
    RVTEST_FENCEI                              // sync I-cache: a prior store may have updated this executable region
    \TEST_CASE\()_3:
    jalr ra, 0(a4)
    nop
    nop
1:
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)                 // Signature update

    LI(a4, NOP)                                              // Value to write (NOP)
    // Store Access Check
    LA(a5, \ADDRESS)                                      // Address to be verified

    \TEST_CASE\()_1:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)

    LA(a5, \ADDRESS)                                      // Address to be verified

    \TEST_CASE\()_2:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)                 // Signature update

.endm
