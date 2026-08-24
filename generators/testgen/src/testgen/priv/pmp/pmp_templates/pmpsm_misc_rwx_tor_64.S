.macro VERIFICATION_RWX ADDRESS TEST_CASE

    RVTEST_FENCEI

    // Execution Access Check
    LA (a4, \ADDRESS)
    LA(x1, 1f)                            // Store the return Address in x1
    jalr ra, 0(a4)
    nop
    nop
1:
    nop
    nop

    addi a4, a4, -4                       // REGIONSTART - 4
    LA(x1, 2f)                            // Store the return Address in x1
    jalr ra, 0(a4)
    nop
    nop
2:
    nop
    nop

    addi a4, a4, 8                        // REGIONSTART + 4
    LA(x1, 3f)                            // Store the return Address in x1
    jalr ra, 0(a4)
    nop
    nop
3:
    nop
    nop

    LI(t0, g-8)
    add a4, a4, t0                        // REGIONSTART + g - 4
    LA(x1, 4f)                            // Store the return Address in x1
    jalr ra, 0(a4)
    nop
    nop
4:
    nop
    nop

    addi a4, a4, 4                      // REGIONSTART + g
    LA(x1, 5f)                            // Store the return Address in x1
    jalr ra, 0(a4)
    nop
    nop
5:
    nop
    nop

    LI(a4, DOUBLE_NOP)                                              // Value to write (DOUBLE_NOP)
    // Store Access Check
    LA(a5, \ADDRESS)                                      // Address to be verified

    \TEST_CASE\()_1:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)


    addi a5, a5, -4                                       // REGIONSTART - 4

    \TEST_CASE\()_2:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)


    addi a5, a5, 8                                        // REGIONSTART + 4

    \TEST_CASE\()_3:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)


    LI(t0, g-8)
    add a5, a5, t0                                        // REGIONSTART + g - 4

    \TEST_CASE\()_4:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_4, test_4_str)


    addi a5, a5, 4                                        // REGIONSTART + g

    \TEST_CASE\()_5:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_5, test_5_str)

    LA(a5, \ADDRESS)                                      // Address to be verified

    \TEST_CASE\()_6:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_6, test_6_str)


    addi a5, a5, -4

    \TEST_CASE\()_7:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_7, test_7_str)


    addi a5, a5, 8

    \TEST_CASE\()_8:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_8, test_8_str)


    LI(t0, g-8)
    add a5, a5, t0

    \TEST_CASE\()_9:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_9, test_9_str)


    addi a5, a5, 4

    \TEST_CASE\()_10:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_10, test_10_str)

.endm
