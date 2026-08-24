// ---------------------------------------------------------------------------
// VERIFICATION_RWX  ADDRESS, TEST_CASE
//   Attempts a store (expected to fault — write not permitted) then a load
//   (expected to succeed — read is permitted) to ADDRESS.
// ---------------------------------------------------------------------------
.macro VERIFICATION_RWX ADDRESS, TEST_CASE
    LA(a5, \ADDRESS)
    \TEST_CASE\()_1:
    sw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4,\TEST_CASE\()_1,test_2_str)
    \TEST_CASE\()_2:
    lw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4,\TEST_CASE\()_2,test_1_str)
.endm
