/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_hcross_svnapot.c - Hypervisor x Svnapot Cross Tests
 *
 * See DOCS/testplan/Hypervisor_cross_test_plan.md Group 6.
 *
 * HCROSS-SVNAPOT-01: G-stage 64 KiB NAPOT basic translation
 * HCROSS-SVNAPOT-02: G-stage NAPOT reserved encoding fault
 * HCROSS-SVNAPOT-03: Both VS-stage and G-stage using NAPOT
 */

/* ===================================================================
 * HCROSS-SVNAPOT-01: G-stage 64 KiB NAPOT basic translation
 *
 * Setup: VS-stage Bare (identity GVA->GPA), G-stage Sv39x4
 *        ts2_setup_full provides kernel/UART at 2MB + test region at 4KB
 * Action: Override first 16 G-stage PTEs (64 KiB) with NAPOT PTE
 * Verify: VS-mode reads/writes all 16 pages successfully
 * =================================================================== */
TEST_REGISTER(test_hcross_svnapot_01);
bool test_hcross_svnapot_01(void) {
    TEST_BEGIN("HCROSS-SVNAPOT-01: G-stage 64 KiB NAPOT basic translation");

    if (!H_AVAILABLE) TEST_SKIP("H extension not available");
    if (!SVNAPOT_AVAILABLE) TEST_SKIP("Svnapot not available");

    two_stage_ctx_t ctx;

    /* Full setup: VS-stage Bare, G-stage Sv39x4.
     * Maps kernel/UART at 2MB and test region at 4KB in G-stage. */
    ts2_setup_full(&ctx, SATP_MODE_BARE, SUITE_HGATP_MODE);

    /* Override first 64 KiB (16 pages) of test region with NAPOT PTE */
    uintptr_t test_gpa = TEST_REGION_BASE;
    uintptr_t test_spa = test_gpa;  /* identity */

    uintptr_t napot_gpte = napot_make_pte(test_spa,
                                           PTE_V | PTE_R | PTE_W | PTE_U |
                                           PTE_A | PTE_D);
    gstage_napot_install_pte(&ctx.g_ctx, test_gpa, napot_gpte);

    /* VS-mode: access all 16 pages within the 64 KiB NAPOT region */
    uintptr_t result = two_stage_run_in_vs(&ctx, vs_access_all_16_pages,
                                           test_gpa);

    TEST_ASSERT("G-stage NAPOT GPA->SPA translation: all 16 pages accessible",
                result == 0);

    ts2_finish(&ctx);
    TEST_END();
}

/* ===================================================================
 * HCROSS-SVNAPOT-02: G-stage NAPOT reserved encoding fault
 *
 * Setup: VS-stage Bare, G-stage Sv39x4 with full mappings
 * Action: Override test region with NAPOT PTE using reserved encoding
 *         (ppn[0][3:0]=0001 instead of valid 1000)
 * Verify: VS-mode load triggers guest-page-fault (cause=21)
 * =================================================================== */
TEST_REGISTER(test_hcross_svnapot_02);
bool test_hcross_svnapot_02(void) {
    TEST_BEGIN("HCROSS-SVNAPOT-02: G-stage NAPOT reserved encoding fault");

    if (!H_AVAILABLE) TEST_SKIP("H extension not available");
    if (!SVNAPOT_AVAILABLE) TEST_SKIP("Svnapot not available");

    two_stage_ctx_t ctx;
    ts2_setup_full(&ctx, SATP_MODE_BARE, SUITE_HGATP_MODE);

    /* Override with reserved NAPOT encoding (ppn[0] low 4 bits = 0001) */
    uintptr_t test_gpa = TEST_REGION_BASE;
    uintptr_t test_spa = test_gpa;
    uintptr_t reserved_gpte = napot_make_reserved_pte(test_spa,
                                                       PTE_V | PTE_R | PTE_W |
                                                       PTE_U | PTE_A | PTE_D,
                                                       0x1);
    gstage_napot_install_pte(&ctx.g_ctx, test_gpa, reserved_gpte);

    /* VS-mode load should trigger guest-page-fault */
    trap_expect_begin();
    two_stage_run_in_vs(&ctx, test_vs_load, test_gpa);
    trap_expect_end();

    TEST_ASSERT("guest-page-fault triggered for reserved NAPOT encoding",
                trap_was_triggered());
    if (trap_was_triggered()) {
        TEST_ASSERT_EQ("cause is load guest-page-fault (21)",
                       trap_get_cause(),
                       (uintptr_t)CAUSE_LOAD_GUEST_PAGE_FAULT);
    }

    ts2_finish(&ctx);
    TEST_END();
}

/* ===================================================================
 * HCROSS-SVNAPOT-03: Both VS-stage and G-stage using NAPOT
 *
 * Setup: VS-stage Sv39, G-stage Sv39x4 (both active)
 *        ts2_setup_full provides standard mappings in both stages
 * Action: Override first 64 KiB in both stages with NAPOT PTEs
 * Verify: VS-mode reads/writes all 16 pages through two-stage NAPOT
 * =================================================================== */
TEST_REGISTER(test_hcross_svnapot_03);
bool test_hcross_svnapot_03(void) {
    TEST_BEGIN("HCROSS-SVNAPOT-03: Both VS-stage and G-stage use NAPOT");

    if (!H_AVAILABLE) TEST_SKIP("H extension not available");
    if (!SVNAPOT_AVAILABLE) TEST_SKIP("Svnapot not available");

    two_stage_ctx_t ctx;

    /* Full setup: both stages active with standard mappings */
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    uintptr_t test_gva = TEST_REGION_BASE;
    uintptr_t test_gpa = test_gva;  /* identity GVA->GPA */
    uintptr_t test_spa = test_gpa;  /* identity GPA->SPA */

    /* Override VS-stage with NAPOT PTE */
    uintptr_t vs_napot_pte = napot_make_pte(test_gpa,
                                             PTE_V | PTE_R | PTE_W |
                                             PTE_A | PTE_D);
    vstage_napot_install_pte(&ctx, test_gva, vs_napot_pte);

    /* Override G-stage with NAPOT PTE */
    uintptr_t gs_napot_gpte = napot_make_pte(test_spa,
                                              PTE_V | PTE_R | PTE_W | PTE_U |
                                              PTE_A | PTE_D);
    gstage_napot_install_pte(&ctx.g_ctx, test_gpa, gs_napot_gpte);

    /* VS-mode: access all 16 pages through two-stage NAPOT */
    uintptr_t result = two_stage_run_in_vs(&ctx, vs_access_all_16_pages,
                                           test_gva);

    TEST_ASSERT("Two-stage NAPOT translation: all 16 pages accessible",
                result == 0);

    ts2_finish(&ctx);
    TEST_END();
}
