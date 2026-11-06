// ai_macros.h
// Shared helpers for the rule-derived tests in tests_ai/.
// SPDX-License-Identifier: Apache-2.0
//
// These tests build with NEEDS_SIGNATURE: false. Expected values are written into each
// test by its generator, so no reference model is involved. This header adds two things
// on top of the standard framework (tests/env):
//
// 1. Checks. AI_CHECK compares a register with the next value in the test's expected-value
//    table. x3 (the framework data pointer) walks the table in program order. A mismatch
//    calls the standard failure reporter through the same LREG/beq/jal sequence that
//    RVTEST_SIGUPD uses. The expected value is outside the signature region, so the report
//    prints "Expected value unavailable" with the table pointer; each check's description
//    string therefore carries the expected value(s) itself.
//
// 2. Trap windows. In a build without a signature, the framework trap handlers record each
//    trap in the trap log (TRAP LOG in tests/env/rvtest_trap_handler.h) and fail the test on
//    any trap the test did not permit. A window permits traps with AI_ALLOW, runs the
//    instructions under test in any privilege mode, and reads the outcome with AI_OUTCOME
//    and AI_LOG. T-SBI calls work inside a window and are not logged.
//
// Register use (E-compatible, x1-x15 only):
//   x2 signature pointer (reserved by the framework), x3 table pointer, x4/x5 check
//   temporaries, x10-x12 T-SBI arguments, x13-x15 trap-window state and results.
//   Tests draw operand registers from x1, x6-x9 and, when not in use above, x10-x15.

#ifndef AI_MACROS_H
#define AI_MACROS_H

#define AI_TP x3

// Load the next table entry into _R and advance the table pointer.
#define AI_LOAD(_R)                                         \
    LREG _R, 0(AI_TP)                                      ;\
    addi AI_TP, AI_TP, REGWIDTH

// Skip _N table entries.
#define AI_SKIP(_N)                                         \
    addi AI_TP, AI_TP, (_N)*REGWIDTH

// Compare _R with the next table entry. _LBL labels the instruction under test and
// _STR the description string; both are reported on a mismatch.
#define AI_CHECK(_R, _LBL, _STR)                            \
    .option push                                           ;\
    .option norvc                                          ;\
    LREG x4, 0(AI_TP)                                      ;\
    beq  x4, _R, 1f                                        ;\
    jal  x5, failedtest_x5_x4                              ;\
    RVTEST_WORD_PTR _LBL                                   ;\
    RVTEST_WORD_PTR _STR                                   ;\
1:                                                         ;\
    addi AI_TP, AI_TP, REGWIDTH                            ;\
    .option pop

// Pass when _R equals either of the next two table entries (two legal outcomes).
#define AI_CHECK2(_R, _LBL, _STR)                           \
    .option push                                           ;\
    .option norvc                                          ;\
    LREG x4, 0(AI_TP)                                      ;\
    beq  x4, _R, 1f                                        ;\
    LREG x4, REGWIDTH(AI_TP)                               ;\
    beq  x4, _R, 1f                                        ;\
    jal  x5, failedtest_x5_x4                              ;\
    RVTEST_WORD_PTR _LBL                                   ;\
    RVTEST_WORD_PTR _STR                                   ;\
1:                                                         ;\
    addi AI_TP, AI_TP, 2*REGWIDTH                          ;\
    .option pop

// Pass when _R equals any of the next three table entries.
#define AI_CHECK3(_R, _LBL, _STR)                           \
    .option push                                           ;\
    .option norvc                                          ;\
    LREG x4, 0(AI_TP)                                      ;\
    beq  x4, _R, 1f                                        ;\
    LREG x4, REGWIDTH(AI_TP)                               ;\
    beq  x4, _R, 1f                                        ;\
    LREG x4, 2*REGWIDTH(AI_TP)                             ;\
    beq  x4, _R, 1f                                        ;\
    jal  x5, failedtest_x5_x4                              ;\
    RVTEST_WORD_PTR _LBL                                   ;\
    RVTEST_WORD_PTR _STR                                   ;\
1:                                                         ;\
    addi AI_TP, AI_TP, 3*REGWIDTH                          ;\
    .option pop

// Variants for checking x5 itself (e.g. a computed predicate): AI_CHECK's failure path links through x5, which
// would overwrite the value before the reporter saves it. These compare against x13 and link through x14
// (failedtest_x14_x13 saves x4 and x5 first), so they clobber x13 even when the check passes. Use them only
// where x13 is dead (outside trap windows in tests that keep x13-x15 for windows).
#define AI_CHECK_X5(_LBL, _STR)                             \
    .option push                                           ;\
    .option norvc                                          ;\
    LREG x13, 0(AI_TP)                                     ;\
    beq  x13, x5, 1f                                       ;\
    jal  x14, failedtest_x14_x13                           ;\
    RVTEST_WORD_PTR _LBL                                   ;\
    RVTEST_WORD_PTR _STR                                   ;\
1:                                                         ;\
    addi AI_TP, AI_TP, REGWIDTH                            ;\
    .option pop

#define AI_CHECK2_X5(_LBL, _STR)                            \
    .option push                                           ;\
    .option norvc                                          ;\
    LREG x13, 0(AI_TP)                                     ;\
    beq  x13, x5, 1f                                       ;\
    LREG x13, REGWIDTH(AI_TP)                              ;\
    beq  x13, x5, 1f                                       ;\
    jal  x14, failedtest_x14_x13                           ;\
    RVTEST_WORD_PTR _LBL                                   ;\
    RVTEST_WORD_PTR _STR                                   ;\
1:                                                         ;\
    addi AI_TP, AI_TP, 2*REGWIDTH                          ;\
    .option pop

#define AI_CHECK3_X5(_LBL, _STR)                            \
    .option push                                           ;\
    .option norvc                                          ;\
    LREG x13, 0(AI_TP)                                     ;\
    beq  x13, x5, 1f                                       ;\
    LREG x13, REGWIDTH(AI_TP)                              ;\
    beq  x13, x5, 1f                                       ;\
    LREG x13, 2*REGWIDTH(AI_TP)                            ;\
    beq  x13, x5, 1f                                       ;\
    jal  x14, failedtest_x14_x13                           ;\
    RVTEST_WORD_PTR _LBL                                   ;\
    RVTEST_WORD_PTR _STR                                   ;\
1:                                                         ;\
    addi AI_TP, AI_TP, 3*REGWIDTH                          ;\
    .option pop

// ---------------------------------------------------------------- trap windows
// Open a window: permit up to _N traps and save the trap count in x13.
#define AI_ALLOW(_N)                                        \
    LA(  x4, rvtest_trap_allow)                            ;\
    LI(  x5, _N)                                           ;\
    SREG x5, 0(x4)                                         ;\
    LA(  x4, rvtest_trap_count)                            ;\
    LREG x13, 0(x4)

// _R = word _W (a TRAPLOG_* index) of the last logged trap; x4 = its entry address.
#define AI_LOG(_R, _W)                                      \
    LA(  x4, rvtest_trap_count)                            ;\
    LREG x5, 0(x4)                                         ;\
    addi x5, x5, -1                                        ;\
    andi x5, x5, RVTEST_TRAP_LOG_N-1                       ;\
    slli x5, x5, TRAPLOG_ENTRY_SHIFT                       ;\
    LA(  x4, rvtest_trap_log)                              ;\
    add  x4, x4, x5                                        ;\
    LREG _R, (_W)*REGWIDTH(x4)

// Close a window: permit no more traps. x13 = number of traps in the window, and
// x14 = xcause of the last one, or -1 when there was none.
#define AI_OUTCOME                                          \
    LA(  x4, rvtest_trap_allow)                            ;\
    SREG x0, 0(x4)                                         ;\
    LA(  x4, rvtest_trap_count)                            ;\
    LREG x5, 0(x4)                                         ;\
    sub  x13, x5, x13                                      ;\
    li   x14, -1                                           ;\
    beqz x13, 3f                                           ;\
    AI_LOG(x14, TRAPLOG_CAUSE)                             ;\
3:

// x15 = the privilege mode the last logged trap came from, read from the handler's
// xPP and xPV fields: 0 U, 1 S/HS, 3 M, 4 VU, 5 VS. Clobbers x13 and x14.
#if __riscv_xlen == 64
  #define AI_MPV  LREG x14, TRAPLOG_STATUS*REGWIDTH(x4); srli x14, x14, 39   /* mstatus.MPV */
#else
  #define AI_MPV  srli x14, x14, 7                                           /* mstatush.MPV */
#endif
#define AI_ORIGIN                                           \
    AI_LOG(x13, TRAPLOG_VECT)                              ;\
    andi x13, x13, 3          /* 3 M, 1 S/HS, 2 VS */      ;\
    LREG x15, TRAPLOG_STATUS*REGWIDTH(x4)                  ;\
    LREG x14, TRAPLOG_STATUS2*REGWIDTH(x4)                 ;\
    li   x5, 3                                             ;\
    bne  x13, x5, 1f                                       ;\
    srli x15, x15, 11         /* mstatus.MPP */            ;\
    andi x15, x15, 3                                       ;\
    AI_MPV                                                 ;\
    andi x14, x14, 1                                       ;\
    j    2f                                                ;\
1:  srli x15, x15, 8          /* sstatus.SPP */            ;\
    andi x15, x15, 1                                       ;\
    srli x14, x14, 7          /* hstatus.SPV (0 w/o H) */  ;\
    andi x14, x14, 1                                       ;\
    addi x13, x13, -2                                      ;\
    seqz x13, x13             /* VS handler: from VU/VS */ ;\
    or   x14, x14, x13                                     ;\
2:  slli x14, x14, 2                                       ;\
    or   x15, x15, x14

#endif // AI_MACROS_H
