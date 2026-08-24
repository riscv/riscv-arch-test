.macro VERIFICATION_RWX ADDRESS, TEST_CASE

    LA(a5, \ADDRESS)                                        // Address to be verified
    \TEST_CASE\()_1:
    sw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4,\TEST_CASE\()_1,test_1_str)
    \TEST_CASE\()_2:
    lw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4,\TEST_CASE\()_2,test_2_str)

.endm
