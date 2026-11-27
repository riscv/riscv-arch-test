/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * common/hyp/tests_2stage/test_group09_sum.c
 *
 * Group 9 - SUM semantics (TS-SUM-01..03)
 *
 * Spec basis:
 *   - vsstatus.SUM controls VS-stage U-bit access policy: when SUM=0
 *     a VS-mode (S-level) load/store cannot touch a U=1 VS-stage
 *     leaf PTE; when SUM=1 it can.
 *   - G-stage always treats every guest access as U-mode; the SUM
 *     bit has no meaning at G-stage. A G-stage U=0 leaf must always
 *     fault, regardless of vsstatus.SUM.
 *
 * Note: Group 7's TS-PERM-11/12 already covers TS-SUM-01/02 from the
 * permission-cross perspective. This file repeats them in the SUM-
 * dedicated wording mandated by the test plan, plus the cross-stage
 * TS-SUM-03.
 * =================================================================== */

#ifndef SUITE_HGATP_MODE
#error "SUITE_HGATP_MODE must be defined before including this file"
#endif
#ifndef SUITE_VSATP_MODE
#error "SUITE_VSATP_MODE must be defined before including this file"
#endif


#define G9_VS_RWX_U   (PTE_V|PTE_R|PTE_W|PTE_X|PTE_U|PTE_A|PTE_D)
#define G9_G_RWX_NOU  (PTE_V|PTE_R|PTE_W|PTE_X|PTE_A|PTE_D)

/* SUM choice: uses shared g_vs_sum_value / vs_load_with_sum
 * from test_helpers.h. */

/* ===================================================================
 * TS-SUM-01: VS PTE U=1, vsstatus.SUM=0; VS-mode load -> page-fault.
 * =================================================================== */
TEST_REGISTER(test_ts_sum_01_vs_u1_sum0);
bool test_ts_sum_01_vs_u1_sum0(void) {
    TEST_BEGIN("TS-SUM-01: VS U=1 + SUM=0 -> page-fault (13)");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_fault_page;
    ts2_setup_with_vs_victim(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE, va, G9_VS_RWX_U);

    g_vs_sum_value = 0;
    bool ok = ts2_run_check_fault(&ctx, vs_load_with_sum, va,
                                  CAUSE_LOAD_PAGE_FAULT);
    TEST_ASSERT("cause = load-page-fault (13) [SUM=0 blocks U=1]", ok);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-SUM-02: VS PTE U=1, vsstatus.SUM=1; VS-mode load -> success.
 * =================================================================== */
TEST_REGISTER(test_ts_sum_02_vs_u1_sum1);
bool test_ts_sum_02_vs_u1_sum1(void) {
    TEST_BEGIN("TS-SUM-02: VS U=1 + SUM=1 -> success");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_fault_page;
    ts2_setup_with_vs_victim(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE, va, G9_VS_RWX_U);

    g_vs_sum_value = 1;
    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, vs_load_with_sum, va);
    bool fired = trap_was_triggered();
    trap_expect_end();
    ts2_finish(&ctx);
    TEST_ASSERT("no fault (SUM=1 permits VS->U access)", !fired);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-SUM-03: VS PTE U=1, G PTE U=0, vsstatus.SUM=1; VS-mode load.
 * SUM=1 covers VS-stage, but G-stage U=0 still raises a guest-page-
 * fault (cause=21). Demonstrates SUM has no influence on G-stage.
 * =================================================================== */
TEST_REGISTER(test_ts_sum_03_g_u0_independent);
bool test_ts_sum_03_g_u0_independent(void) {
    TEST_BEGIN("TS-SUM-03: G U=0 unaffected by SUM -> guest-page-fault (21)");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_fault_page;
    /* VS U=1, G no-U (RWX without U bit). */
    ts2_setup_with_dual_victim(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE, va,
                               G9_VS_RWX_U, G9_G_RWX_NOU);

    g_vs_sum_value = 1;
    bool ok = ts2_run_check_fault(&ctx, vs_load_with_sum, va,
                                  CAUSE_LOAD_GUEST_PAGE_FAULT);
    TEST_ASSERT("cause = load-guest-page-fault (21) [G-stage U=0 fault]", ok);
    HYP_TEST_END();
}
