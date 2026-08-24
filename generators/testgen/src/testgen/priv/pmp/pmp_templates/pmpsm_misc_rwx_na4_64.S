.macro VERIFICATION_RWX ADDRESS TEST_CASE

    // Execution Access Check
    LA (a4, \ADDRESS)
    LA(x1, 1f)                            // Store the return Address in x1
    RVTEST_FENCEI                              // sync I-cache: a prior store may have updated this executable region
    jalr ra, 0(a4)
    nop
    nop
1:
    nop
    nop

    addi a4, a4, -4                     // REGIONSTART - 4
    LA(x1, 2f)                            // Store the return Address in x1
    jalr ra, 0(a4)
    nop
    nop
2:
    nop
    nop

    addi a4, a4, 8                      // REGIONSTART + 4
    LA(x1, 3f)                            // Store the return Address in x1
    jalr ra, 0(a4)
    nop
    nop
3:
    nop
    nop

    LI(a4, DOUBLE_NOP)                                              // Value to write (DOUBLE_NOP)

    // Load & Store Access Check
    LA(a5, \ADDRESS)                                         // Address to be verified

    \TEST_CASE\()_1:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)

    \TEST_CASE\()_2:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)


    addi a5, a5, -4                                          // REGIONSTART - 4

    \TEST_CASE\()_3:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)

    \TEST_CASE\()_4:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_4, test_4_str)


    addi a5, a5, 8                                           // REGIONSTART + 4

    \TEST_CASE\()_5:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_5, test_5_str)

    \TEST_CASE\()_6:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_6, test_6_str)

.endm
