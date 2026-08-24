.macro VERIFICATION_X ADDRESS TEST_CASE      // {jalr, sw, lw} at start of region
    // Execution Access Check
    LA (a4, \ADDRESS)
    LA(x1, 1f)                            // Store the return Address in x1
    \TEST_CASE\()_1:
    jalr ra, 0(a4)
    nop
1:
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)

.endm

.macro VERIFICATION_W ADDRESS TEST_CASE      // {jalr, sw, lw} at start of region

    // Store Access Check
    LA(a5, \ADDRESS)                                         // Address to be verified
    LI(a4, DOUBLE_NOP)                                              // Value to write (DOUBLE_NOP)
    \TEST_CASE\()_2:
    sw a4, 0(a5)                                             // Word store test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)

.endm

.macro VERIFICATION_R ADDRESS TEST_CASE      // {jalr, sw, lw} at start of region

    LA(a5, \ADDRESS)
    LI(a4, DOUBLE_NOP)                                              // Value to write (DOUBLE_NOP)
    // Load Access Check
    \TEST_CASE\()_3:
    lw a4, 0(a5)                                             // Word load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)

.endm
