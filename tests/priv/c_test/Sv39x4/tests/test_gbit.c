/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 12: G-bit ignored at G-stage (GGBIT-01/02)
 *
 * Spec anchors:
 *   norm:gstage_g_bit_ignored - The G (global) bit in G-stage page
 *                               table entries is ignored: it is
 *                               reserved for future use and must
 *                               not affect translation behavior.
 *
 * GGBIT-01: G=1 leaf -> normal r/w succeeds
 * GGBIT-02: G=0 vs G=1 produce identical translation behavior
 *
 * The G-bit lives at PTE bit 5 (PTE_G). We construct two contexts
 * for GGBIT-02 to compare behavior bit-for-bit.
 * =================================================================== */

/* GGBIT-01: G=1 leaf permits VS-mode r/w */
TEST_REGISTER(test_ggbit_01_g1_ok);
bool test_ggbit_01_g1_ok(void) {
    TEST_BEGIN("GGBIT-01: G=1 G-stage leaf permits VS-mode r/w");

    two_stage_ctx_t ctx;
    /* Same as default flags but with G-bit set. */
    uintptr_t flags = G_FLAGS_RWXU_AD | PTE_G;
    _setup_with_victim(&ctx, (uintptr_t)test_fault_page, flags);

    *(volatile uint64_t *)test_fault_page = 0;
    uintptr_t r = two_stage_run_in_vs(&ctx, test_vs_read_write,
                                      (uintptr_t)test_fault_page);
    TEST_ASSERT("G=1 leaf VS r/w returns 0", r == 0);

    two_stage_cleanup(&ctx);
    HYP_TEST_END();
}

/* GGBIT-02: G=0 vs G=1 produce identical translation results
 *
 * Run the same VS-mode r/w sequence twice, once with G=0 and once
 * with G=1. Both must succeed and return the same value, proving
 * the G-bit has no observable effect at G-stage. */
TEST_REGISTER(test_ggbit_02_g0_vs_g1);
bool test_ggbit_02_g0_vs_g1(void) {
    TEST_BEGIN("GGBIT-02: G=0 and G=1 produce identical G-stage behavior");

    /* Run with G=0 (default flags). */
    two_stage_ctx_t ctx0;
    _setup_with_victim(&ctx0, (uintptr_t)test_fault_page, G_FLAGS_RWXU_AD);
    *(volatile uint64_t *)test_fault_page = 0;
    uintptr_t r0 = two_stage_run_in_vs(&ctx0, test_vs_read_write,
                                       (uintptr_t)test_fault_page);
    two_stage_cleanup(&ctx0);
    hyp_reset_state();

    /* Run with G=1. */
    two_stage_ctx_t ctx1;
    _setup_with_victim(&ctx1, (uintptr_t)test_fault_page,
                       G_FLAGS_RWXU_AD | PTE_G);
    *(volatile uint64_t *)test_fault_page = 0;
    uintptr_t r1 = two_stage_run_in_vs(&ctx1, test_vs_read_write,
                                       (uintptr_t)test_fault_page);
    two_stage_cleanup(&ctx1);

    TEST_ASSERT("G=0 r/w returns 0", r0 == 0);
    TEST_ASSERT("G=1 r/w returns 0", r1 == 0);
    TEST_ASSERT("G=0 and G=1 results match", r0 == r1);
    HYP_TEST_END();
}
