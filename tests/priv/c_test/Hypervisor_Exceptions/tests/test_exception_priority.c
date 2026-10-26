/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * Test Group 7: Exception priority
 *
 * Tests PRIO-01 through PRIO-05 verify exception priority rules.
 */

#include "hyp_test_helpers.h"

/* Helper trampoline for PRIV_DO (requires expression, not asm stmt). */
static uintptr_t hs_exec_ecall(uintptr_t arg) {
    (void)arg;
    extern uintptr_t ecall_args[2];
    ecall_args[0] = 0;  /* NOT ECALL_GOTO_PRIV — record as trap */
    asm volatile("ecall" ::: "memory");
    return 0;
}

/* ------------------------------------------------------------------
 * PRIO-01: virtual-instruction priority lower than illegal-instruction
 * ------------------------------------------------------------------ */
TEST_REGISTER(priority_virtual_vs_illegal);
bool priority_virtual_vs_illegal(void) {
    TEST_BEGIN("PRIO-01: Verify illegal-instruction takes priority over virtual-instruction");

    /* mstatus.TW=1 causes WFI in VS-mode to raise illegal-inst (cause=2),
     * even though VTW=1 alone would cause virtual-inst (cause=22).
     * This proves illegal-instruction has higher priority.
     * TW is a config bit: set/clear it via the tsbi_csr_* accessor (this
     * suite runs in S(HS)-mode, so a raw csrr/csrw mstatus would trap illegal). */
    tsbi_csr_set(CSR_MSTATUS, 1UL << 21);   /* Set TW */
    hstatus_set_vtw(true);

    EXPECT_ILLEGAL_INST(run_in_vs_mode(vs_exec_wfi, 0));

    /* Cleanup */
    tsbi_csr_clear(CSR_MSTATUS, 1UL << 21);
    hstatus_set_vtw(false);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * PRIO-02: guest-page-fault vs page-fault priority
 * ------------------------------------------------------------------ */
TEST_REGISTER(priority_gpf_vs_pf);
bool priority_gpf_vs_pf(void) {
    TEST_BEGIN("PRIO-02: Verify guest-page-fault vs page-fault priority");

    TEST_SKIP("requires two-stage simultaneous fault");

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * PRIO-03: VS-mode ECALL cause=10
 * ------------------------------------------------------------------ */
TEST_REGISTER(priority_vs_ecall_cause);
bool priority_vs_ecall_cause(void) {
    TEST_BEGIN("PRIO-03: Verify VS-mode ECALL has cause=10");

    trap_expect_begin();
    run_in_vs_mode(vs_exec_ecall, 0);
    TEST_ASSERT("VS ecall trap triggered", trap_was_triggered());
    TEST_ASSERT_EQ("cause == 10 (ecall from VS)",
                   trap_get_cause(), (uintptr_t)10);
    trap_expect_end();

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * PRIO-04: HS-mode ECALL cause=9
 * ------------------------------------------------------------------ */
TEST_REGISTER(priority_hs_ecall_cause);
bool priority_hs_ecall_cause(void) {
    TEST_BEGIN("PRIO-04: Verify HS-mode ECALL has cause=9");

    /* Must execute ecall from HS-mode (S-mode with V=0), not M-mode.
     * M-mode ecall would produce cause=11, not cause=9. */
    goto_priv(PRIV_S);
    PRIV_DO(hs_exec_ecall(0));
    goto_priv(PRIV_M);
    CHECK_TRAP("HS ecall trap triggered", 9);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * PRIO-05: VU-mode ECALL cause=8
 * ------------------------------------------------------------------ */
TEST_REGISTER(priority_vu_ecall_cause);
bool priority_vu_ecall_cause(void) {
    TEST_BEGIN("PRIO-05: Verify VU-mode ECALL has cause=8");

    trap_expect_begin();
    run_in_vu_mode(vs_exec_ecall, 0);
    TEST_ASSERT("VU ecall trap triggered", trap_was_triggered());
    TEST_ASSERT_EQ("cause == 8 (ecall from VU/U)",
                   trap_get_cause(), (uintptr_t)CAUSE_ECALL_FROM_U);
    trap_expect_end();

    HYP_TEST_END();
}
