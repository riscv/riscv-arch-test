/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_accessfault.c - Group 2: Access-Fault Address Exceptions
 *
 * Tests VSTVAL-LAF-01, VSTVAL-SAF-01, VSTVAL-IAF-01
 *
 * Validates that when a PMP-induced access-fault is delegated to VS-mode,
 * vstval is written with the faulting guest virtual address.
 *
 * Setup: PMP restricts specific PA, two-stage identity map (VA=GPA=PA).
 * hedeleg delegates access-faults to VS-mode.
 *
 * The PMP CSRs are M-level, so all pmp_* configuration goes through the
 * M-mode-excursion wrappers in shvstvala_helpers.h (see the note there).
 */

/* ------------------------------------------------------------------ */
/* VSTVAL-LAF-01: load access-fault, PMP denies read                  */
/* ------------------------------------------------------------------ */
TEST_REGISTER(test_shvstvala_laf_01);
bool test_shvstvala_laf_01(void) {
    TEST_BEGIN("VSTVAL-LAF-01: load access-fault vstval == faulting VA");

    /* Delegate load access-fault (cause=5) to VS-mode */
    hyp_delegate_to_vs((1UL << 5), 0);

    /* PMP: deny all access on test_pmp_page (4KB), allow everything else
     * through the catch-all entry -- installed in one M-mode excursion.
     * Note: W-only (0b010) is a reserved PMP encoding; use 0 (no perms). */
    pmp_deny_page_m(PMP_RESTRICTED_PA, 0x1000, 0);

    g_shvstvala_vstval = 0;
    g_shvstvala_cause  = 0;

    /* Two-stage identity map so VA == GPA == PA */
    two_stage_ctx_t ctx;
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    uintptr_t target_va = PMP_RESTRICTED_PA;
    two_stage_run_in_vs(&ctx, vsmode_load_addr, target_va);

    TEST_ASSERT_EQ("vscause == load access-fault (5)",
                   g_shvstvala_cause, (uintptr_t)5);
    TEST_ASSERT_EQ("vstval == faulting VA",
                   g_shvstvala_vstval, target_va);

    two_stage_cleanup(&ctx);
    pmp_restore_open_m();
    hyp_undelegate();
    HYP_TEST_END();
}

/* ------------------------------------------------------------------ */
/* VSTVAL-SAF-01: store access-fault, PMP denies write                */
/* ------------------------------------------------------------------ */
TEST_REGISTER(test_shvstvala_saf_01);
bool test_shvstvala_saf_01(void) {
    TEST_BEGIN("VSTVAL-SAF-01: store access-fault vstval == faulting VA");

    /* Delegate store access-fault (cause=7) to VS-mode */
    hyp_delegate_to_vs((1UL << 7), 0);

    /* PMP: deny write on test_pmp_page (4KB, R only -- no W, no X) */
    pmp_deny_page_m(PMP_RESTRICTED_PA, 0x1000, PMP_R);

    g_shvstvala_vstval = 0;
    g_shvstvala_cause  = 0;

    two_stage_ctx_t ctx;
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    uintptr_t target_va = PMP_RESTRICTED_PA;
    two_stage_run_in_vs(&ctx, vsmode_store_addr, target_va);

    TEST_ASSERT_EQ("vscause == store access-fault (7)",
                   g_shvstvala_cause, (uintptr_t)7);
    TEST_ASSERT_EQ("vstval == faulting VA",
                   g_shvstvala_vstval, target_va);

    two_stage_cleanup(&ctx);
    pmp_restore_open_m();
    hyp_undelegate();
    HYP_TEST_END();
}

/* ------------------------------------------------------------------ */
/* VSTVAL-IAF-01: instruction access-fault, PMP denies execute        */
/* ------------------------------------------------------------------ */
TEST_REGISTER(test_shvstvala_iaf_01);
bool test_shvstvala_iaf_01(void) {
    TEST_BEGIN("VSTVAL-IAF-01: instruction access-fault vstval == target PC");

    /* Delegate instruction access-fault (cause=1) to VS-mode */
    hyp_delegate_to_vs((1UL << 1), 0);

    /* PMP: deny execute on test_pmp_page (4KB, RW only -- no X) */
    pmp_deny_page_m(PMP_RESTRICTED_PA, 0x1000, PMP_RW);

    g_shvstvala_vstval = 0;
    g_shvstvala_cause  = 0;

    two_stage_ctx_t ctx;
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    uintptr_t target_pc = PMP_RESTRICTED_PA;
    two_stage_run_in_vs(&ctx, vsmode_fetch_addr, target_pc);

    TEST_ASSERT_EQ("vscause == instruction access-fault (1)",
                   g_shvstvala_cause, (uintptr_t)1);
    TEST_ASSERT_EQ("vstval == faulting PC",
                   g_shvstvala_vstval, target_pc);

    two_stage_cleanup(&ctx);
    pmp_restore_open_m();
    hyp_undelegate();
    HYP_TEST_END();
}
