/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_hcross_svpbmt.c - Hypervisor x Svpbmt Cross Tests
 *
 * See DOCS/testplan/Hypervisor_cross_test_plan.md Group 7.
 *
 * HCROSS-SVPBMT-01: G-stage PBMT=NC overrides PMA
 * HCROSS-SVPBMT-02: VS-stage PBMT=IO overrides intermediate
 * HCROSS-SVPBMT-03: Both stages nonzero PBMT stacking
 * HCROSS-SVPBMT-04: hgatp.MODE=0 skips G-stage override
 */

/* ===================================================================
 * HCROSS-SVPBMT-01: G-stage PBMT=NC overrides PMA
 *
 * Setup: VS-stage Bare (no VS-stage translation), G-stage Sv39x4
 *        PBMTE enabled in both menvcfg and henvcfg
 *        ts2_setup_full provides kernel/UART + test region mappings
 * Action: Override G-stage test region PTE with PBMT=NC
 * Verify: VS-mode read/write succeeds; G-stage PBMT=NC overrides PMA
 *         to produce intermediate=NC; VS-stage Bare means no further
 *         override, so final=NC.
 *
 * Override chain: PMA -> G-stage PBMT=NC -> intermediate=NC
 *                 VS-stage Bare -> final=NC
 * =================================================================== */
TEST_REGISTER(test_hcross_svpbmt_01);
bool test_hcross_svpbmt_01(void) {
    TEST_BEGIN("HCROSS-SVPBMT-01: G-stage PBMT=NC overrides PMA");

    if (!H_AVAILABLE) TEST_SKIP("H extension not available");
    if (!SVPBMT_AVAILABLE) TEST_SKIP("Svpbmt not available");

    two_stage_ctx_t ctx;

    /* Enable PBMTE in both menvcfg and henvcfg */
    ts2_enable_pbmte();

    /* Full setup: VS-stage Bare, G-stage Sv39x4 */
    ts2_setup_full(&ctx, SATP_MODE_BARE, SUITE_HGATP_MODE);

    uintptr_t test_gpa = TEST_REGION_BASE;

    /* Override G-stage PTE with PBMT=NC */
    g_pte_set_pbmt(&ctx, test_gpa, PBMT_NC);

    /* Verify G-stage PTE has PBMT=NC */
    uintptr_t gpbmt = g_pte_read_pbmt(&ctx, test_gpa);
    TEST_ASSERT_EQ("G-stage PTE PBMT is NC (1)", gpbmt,
                   (uintptr_t)(PBMT_NC >> PTE_PBMT_SHIFT));

    /* VS-mode: read/write should succeed (final=NC is valid) */
    uintptr_t result = two_stage_run_in_vs(&ctx, test_vs_read_write,
                                           test_gpa);
    TEST_ASSERT("G-stage PBMT=NC override: access succeeds", result == 0);

    ts2_finish(&ctx);
    ts2_disable_pbmte();
    TEST_END();
}

/* ===================================================================
 * HCROSS-SVPBMT-02: VS-stage PBMT=IO overrides intermediate
 *
 * Setup: VS-stage Sv39, G-stage Sv39x4, PBMTE enabled
 *        ts2_setup_full provides standard mappings
 * Action: Set G-stage PTE PBMT=0 (PMA), VS-stage PTE PBMT=IO
 * Verify: VS-mode access succeeds
 *
 * Override chain: PMA -> G-stage PBMT=0 (no override) -> intermediate=PMA
 *                 VS-stage PBMT=IO overrides intermediate -> final=IO
 * =================================================================== */
TEST_REGISTER(test_hcross_svpbmt_02);
bool test_hcross_svpbmt_02(void) {
    TEST_BEGIN("HCROSS-SVPBMT-02: VS-stage PBMT=IO overrides intermediate");

    if (!H_AVAILABLE) TEST_SKIP("H extension not available");
    if (!SVPBMT_AVAILABLE) TEST_SKIP("Svpbmt not available");

    two_stage_ctx_t ctx;
    ts2_enable_pbmte();

    /* Both stages active */
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    uintptr_t test_gva = TEST_REGION_BASE;

    /* G-stage: PBMT=0 (no override, intermediate=PMA) */
    g_pte_set_pbmt(&ctx, test_gva, PBMT_PMA);

    /* VS-stage: PBMT=IO overrides intermediate -> final=IO */
    vs_pte_set_pbmt(&ctx, test_gva, PBMT_IO);

    /* Verify PBMT fields */
    TEST_ASSERT_EQ("G-stage PTE PBMT is PMA (0)",
                   g_pte_read_pbmt(&ctx, test_gva), (uintptr_t)0);
    TEST_ASSERT_EQ("VS-stage PTE PBMT is IO (2)",
                   vs_pte_read_pbmt(&ctx, test_gva),
                   (uintptr_t)(PBMT_IO >> PTE_PBMT_SHIFT));

    uintptr_t result = two_stage_run_in_vs(&ctx, test_vs_read_write,
                                           test_gva);
    TEST_ASSERT("VS-stage PBMT=IO override: access succeeds with IO attrs",
                result == 0);

    ts2_finish(&ctx);
    ts2_disable_pbmte();
    TEST_END();
}

/* ===================================================================
 * HCROSS-SVPBMT-03: Both stages nonzero PBMT stacking
 *
 * Setup: VS-stage Sv39, G-stage Sv39x4, PBMTE enabled
 * Action: G-stage PTE with PBMT=NC, VS-stage PTE with PBMT=IO
 * Verify: VS-mode access succeeds; VS-stage override wins
 *
 * Override chain: PMA -> G-stage PBMT=NC -> intermediate=NC
 *                 VS-stage PBMT=IO overrides intermediate=NC -> final=IO
 *
 * VS-stage has higher override priority than G-stage.
 * =================================================================== */
TEST_REGISTER(test_hcross_svpbmt_03);
bool test_hcross_svpbmt_03(void) {
    TEST_BEGIN("HCROSS-SVPBMT-03: Both stages nonzero PBMT override");

    if (!H_AVAILABLE) TEST_SKIP("H extension not available");
    if (!SVPBMT_AVAILABLE) TEST_SKIP("Svpbmt not available");

    two_stage_ctx_t ctx;
    ts2_enable_pbmte();

    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    uintptr_t test_gva = TEST_REGION_BASE;

    /* G-stage: PBMT=NC -> intermediate=NC */
    g_pte_set_pbmt(&ctx, test_gva, PBMT_NC);

    /* VS-stage: PBMT=IO overrides intermediate=NC -> final=IO */
    vs_pte_set_pbmt(&ctx, test_gva, PBMT_IO);

    /* Verify PBMT fields */
    TEST_ASSERT_EQ("G-stage PTE PBMT is NC (1)",
                   g_pte_read_pbmt(&ctx, test_gva),
                   (uintptr_t)(PBMT_NC >> PTE_PBMT_SHIFT));
    TEST_ASSERT_EQ("VS-stage PTE PBMT is IO (2)",
                   vs_pte_read_pbmt(&ctx, test_gva),
                   (uintptr_t)(PBMT_IO >> PTE_PBMT_SHIFT));

    uintptr_t result = two_stage_run_in_vs(&ctx, test_vs_read_write,
                                           test_gva);
    TEST_ASSERT("Two-stage PBMT override: VS-stage IO wins, access succeeds",
                result == 0);

    ts2_finish(&ctx);
    ts2_disable_pbmte();
    TEST_END();
}

/* ===================================================================
 * HCROSS-SVPBMT-04: hgatp.MODE=0 (Bare) skips G-stage override
 *
 * Setup: VS-stage Sv39, G-stage Bare (hgatp.MODE=0), PBMTE enabled
 * Action: VS-stage PTE with PBMT=NC
 * Verify: VS-mode access succeeds
 *
 * Override chain: G-stage Bare -> no G-stage translation -> intermediate=PMA
 *                 VS-stage PBMT=NC overrides intermediate=PMA -> final=NC
 *
 * When hgatp.MODE=0, G-stage is disabled entirely. The PBMT override
 * chain starts from VS-stage, with intermediate=PMA (physical memory
 * attributes).
 * =================================================================== */
TEST_REGISTER(test_hcross_svpbmt_04);
bool test_hcross_svpbmt_04(void) {
    TEST_BEGIN("HCROSS-SVPBMT-04: hgatp.MODE=0 skips G-stage override");

    if (!H_AVAILABLE) TEST_SKIP("H extension not available");
    if (!SVPBMT_AVAILABLE) TEST_SKIP("Svpbmt not available");

    two_stage_ctx_t ctx;
    ts2_enable_pbmte();

    /* hgatp.MODE=0 (Bare): G-stage disabled.
     * ts2_setup_full handles Bare G-stage correctly by skipping
     * G-stage mappings. */
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, HGATP_MODE_BARE);

    uintptr_t test_gva = TEST_REGION_BASE;

    /* VS-stage: PBMT=NC, intermediate=PMA (no G-stage) -> final=NC */
    vs_pte_set_pbmt(&ctx, test_gva, PBMT_NC);

    /* Verify VS-stage PBMT */
    TEST_ASSERT_EQ("VS-stage PTE PBMT is NC (1)",
                   vs_pte_read_pbmt(&ctx, test_gva),
                   (uintptr_t)(PBMT_NC >> PTE_PBMT_SHIFT));

    uintptr_t result = two_stage_run_in_vs(&ctx, test_vs_read_write,
                                           test_gva);
    TEST_ASSERT("hgatp.MODE=0: VS-stage PBMT=NC overrides PMA, access OK",
                result == 0);

    ts2_finish(&ctx);
    ts2_disable_pbmte();
    TEST_END();
}
