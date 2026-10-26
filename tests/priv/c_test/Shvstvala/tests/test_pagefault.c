/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_pagefault.c - Group 1: Page-Fault Address Exceptions
 *
 * Tests VSTVAL-LPF-01, VSTVAL-LPF-02, VSTVAL-SPF-01, VSTVAL-SPF-02,
 *       VSTVAL-IPF-01
 *
 * Validates that when a VS-stage page-fault is delegated to VS-mode,
 * vstval is written with the faulting guest virtual address.
 *
 * Setup: VS-stage (Sv39) with partial mapping + G-stage (Sv39x4) identity.
 * hedeleg delegates page-faults to VS-mode.
 */

/* ------------------------------------------------------------------ */
/* VSTVAL-LPF-01: load page-fault, unmapped VA                        */
/* ------------------------------------------------------------------ */
TEST_REGISTER(test_shvstvala_lpf_01);
bool test_shvstvala_lpf_01(void) {
    TEST_BEGIN("VSTVAL-LPF-01: load page-fault vstval == unmapped VA");

    /* Delegate load page-fault (cause=13) to VS-mode */
    hyp_delegate_to_vs((1UL << 13), 0);

    g_shvstvala_vstval = 0;
    g_shvstvala_cause  = 0;

    /* Setup two-stage: VS-stage Sv39 with identity map for code/stack,
     * UNMAPPED_VA_1 deliberately NOT mapped. G-stage identity. */
    two_stage_ctx_t ctx;
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    /* Execute in VS-mode: load from UNMAPPED_VA_1 */
    two_stage_run_in_vs(&ctx, vsmode_load_addr, UNMAPPED_VA_1);

    TEST_ASSERT_EQ("vscause == load page-fault (13)",
                   g_shvstvala_cause, (uintptr_t)13);
    TEST_ASSERT_EQ("vstval == faulting VA",
                   g_shvstvala_vstval, UNMAPPED_VA_1);

    two_stage_cleanup(&ctx);
    hyp_undelegate();
    HYP_TEST_END();
}

/* ------------------------------------------------------------------ */
/* VSTVAL-SPF-01: store page-fault, read-only page                    */
/* ------------------------------------------------------------------ */
TEST_REGISTER(test_shvstvala_spf_01);
bool test_shvstvala_spf_01(void) {
    TEST_BEGIN("VSTVAL-SPF-01: store page-fault vstval == read-only VA");

    /* Delegate store page-fault (cause=15) to VS-mode */
    hyp_delegate_to_vs((1UL << 15), 0);

    g_shvstvala_vstval = 0;
    g_shvstvala_cause  = 0;

    two_stage_ctx_t ctx;
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    /* Override test_data_area page: V=1,R=1,W=0 (read-only) */
    uintptr_t target_va = (uintptr_t)test_data_area;
    uintptr_t ro_flags = PTE_V | PTE_R | PTE_A | PTE_D;  /* no W */
    two_stage_vs_map(&ctx, target_va, target_va, ro_flags, PT_LEVEL_4K);

    /* VS-mode: store to read-only page */
    two_stage_run_in_vs(&ctx, vsmode_store_addr, target_va);

    TEST_ASSERT_EQ("vscause == store page-fault (15)",
                   g_shvstvala_cause, (uintptr_t)15);
    TEST_ASSERT_EQ("vstval == faulting VA",
                   g_shvstvala_vstval, target_va);

    two_stage_cleanup(&ctx);
    hyp_undelegate();
    HYP_TEST_END();
}

/* ------------------------------------------------------------------ */
/* VSTVAL-IPF-01: instruction page-fault, non-executable page         */
/* ------------------------------------------------------------------ */
TEST_REGISTER(test_shvstvala_ipf_01);
bool test_shvstvala_ipf_01(void) {
    TEST_BEGIN("VSTVAL-IPF-01: instruction page-fault vstval == target PC");

    /* Delegate instruction page-fault (cause=12) to VS-mode */
    hyp_delegate_to_vs((1UL << 12), 0);

    g_shvstvala_vstval = 0;
    g_shvstvala_cause  = 0;

    two_stage_ctx_t ctx;
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    /* Override test_exec_target: V=1,R=1,W=0,X=0 (no execute) */
    uintptr_t target_pc = (uintptr_t)test_exec_target;
    uintptr_t nox_flags = PTE_V | PTE_R | PTE_A | PTE_D;  /* no X */
    two_stage_vs_map(&ctx, target_pc, target_pc, nox_flags, PT_LEVEL_4K);

    /* VS-mode: fetch from non-executable page */
    two_stage_run_in_vs(&ctx, vsmode_fetch_addr, target_pc);

    TEST_ASSERT_EQ("vscause == instruction page-fault (12)",
                   g_shvstvala_cause, (uintptr_t)12);
    TEST_ASSERT_EQ("vstval == faulting PC",
                   g_shvstvala_vstval, target_pc);

    two_stage_cleanup(&ctx);
    hyp_undelegate();
    HYP_TEST_END();
}

/* ------------------------------------------------------------------ */
/* VSTVAL-LPF-02: load page-fault, different VA                       */
/* ------------------------------------------------------------------ */
TEST_REGISTER(test_shvstvala_lpf_02);
bool test_shvstvala_lpf_02(void) {
    TEST_BEGIN("VSTVAL-LPF-02: load page-fault vstval tracks different VA");

    hyp_delegate_to_vs((1UL << 13), 0);

    g_shvstvala_vstval = 0;
    g_shvstvala_cause  = 0;

    two_stage_ctx_t ctx;
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    /* Use UNMAPPED_VA_2 (different from LPF-01) */
    two_stage_run_in_vs(&ctx, vsmode_load_addr, UNMAPPED_VA_2);

    TEST_ASSERT_EQ("vscause == load page-fault (13)",
                   g_shvstvala_cause, (uintptr_t)13);
    TEST_ASSERT_EQ("vstval == different unmapped VA",
                   g_shvstvala_vstval, UNMAPPED_VA_2);

    two_stage_cleanup(&ctx);
    hyp_undelegate();
    HYP_TEST_END();
}

/* ------------------------------------------------------------------ */
/* VSTVAL-SPF-02: store page-fault, unmapped VA                       */
/* ------------------------------------------------------------------ */
TEST_REGISTER(test_shvstvala_spf_02);
bool test_shvstvala_spf_02(void) {
    TEST_BEGIN("VSTVAL-SPF-02: store page-fault vstval == unmapped VA");

    hyp_delegate_to_vs((1UL << 15), 0);

    g_shvstvala_vstval = 0;
    g_shvstvala_cause  = 0;

    two_stage_ctx_t ctx;
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    /* Store to unmapped VA */
    two_stage_run_in_vs(&ctx, vsmode_store_addr, UNMAPPED_VA_1);

    TEST_ASSERT_EQ("vscause == store page-fault (15)",
                   g_shvstvala_cause, (uintptr_t)15);
    TEST_ASSERT_EQ("vstval == unmapped VA",
                   g_shvstvala_vstval, UNMAPPED_VA_1);

    two_stage_cleanup(&ctx);
    hyp_undelegate();
    HYP_TEST_END();
}
