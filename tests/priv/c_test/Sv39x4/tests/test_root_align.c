/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 2: G-stage root page table 16KB alignment (GROOT-01..02)
 *
 * Spec anchors:
 *   norm:hgatp_ppn_op    - hgatp.PPN[1:0] always reads as 0 in Sv*x4
 *   norm:gstage_root_pa  - root table is 16KB, must be 16KB-aligned
 *
 * GROOT-01 verifies the architectural enforcement at the CSR level.
 * GROOT-02 verifies that a *correctly* 16KB-aligned root works for
 * an actual translation walk (smoke test of gstage_pt + two_stage).
 * =================================================================== */

/* GROOT-01: HW masks PPN[1:0] to 0 (any 16KB-misaligned PPN reads
 * back with low 2 bits zero). */
TEST_REGISTER(test_groot_01_ppn_low2_masked);
bool test_groot_01_ppn_low2_masked(void) {
#if SUITE_HGATP_MODE == HGATP_MODE_SV39X4
    TEST_BEGIN("GROOT-01: hgatp.PPN low 2 bits masked to zero (Sv39x4)");
#elif SUITE_HGATP_MODE == HGATP_MODE_SV48X4
    TEST_BEGIN("GROOT-01: hgatp.PPN low 2 bits masked to zero (Sv48x4)");
#elif SUITE_HGATP_MODE == HGATP_MODE_SV57X4
    TEST_BEGIN("GROOT-01: hgatp.PPN low 2 bits masked to zero (Sv57x4)");
#endif

    uintptr_t bases[] = {
        (PLATFORM_MEM_BASE >> PAGE_SHIFT) | 0x1UL,
        (PLATFORM_MEM_BASE >> PAGE_SHIFT) | 0x2UL,
        (PLATFORM_MEM_BASE >> PAGE_SHIFT) | 0x3UL,
    };
    for (unsigned i = 0; i < sizeof(bases)/sizeof(bases[0]); i++) {
        hgatp_write(MAKE_HGATP(SUITE_HGATP_MODE, 0,
                               bases[i] & HGATP_PPN_MASK));
        uintptr_t ppn = HGATP_GET_PPN(hgatp_read());
        TEST_ASSERT_EQ("PPN[1:0] reads 0 (case)", ppn & 0x3UL, 0UL);
    }

    hgatp_set_bare();
    HYP_TEST_END();
}

/* GROOT-02: a correctly 16KB-aligned root table works for translation.
 * Verifies not only alignment + enable, but actual VS-mode read/write
 * through the 16KB root page table (norm:hgatp_mode_x4). */
TEST_REGISTER(test_groot_02_aligned_root_works);
bool test_groot_02_aligned_root_works(void) {
#if SUITE_HGATP_MODE == HGATP_MODE_SV39X4
    TEST_BEGIN("GROOT-02: 16KB-aligned Sv39x4 root activates correctly");
#elif SUITE_HGATP_MODE == HGATP_MODE_SV48X4
    TEST_BEGIN("GROOT-02: 16KB-aligned Sv48x4 root activates correctly");
#elif SUITE_HGATP_MODE == HGATP_MODE_SV57X4
    TEST_BEGIN("GROOT-02: 16KB-aligned Sv57x4 root activates correctly");
#endif

    gpt_pool_reset();
    two_stage_ctx_t ctx;
    two_stage_init(&ctx, SATP_MODE_BARE, SUITE_HGATP_MODE);

    /* root_pt must be 16KB aligned by construction. */
    TEST_ASSERT("root_pt is 16KB aligned",
                ((uintptr_t)ctx.g_ctx.root_pt & (GPT_ROOT_ALIGN - 1)) == 0);

    int rc = two_stage_setup_identity(&ctx, PLATFORM_MEM_BASE,
                                      32UL * 1024UL * 1024UL,
                                      G_FLAGS_RWXU_AD, PT_LEVEL_2M);
    TEST_ASSERT_EQ("identity mapping created", rc, 0);

    /* Activate G-stage and verify translation works end-to-end
     * via VS-mode read/write through the 16KB root. */
    uintptr_t target = (uintptr_t)test_data_area;
    *(volatile uint64_t *)target = 0;
    uintptr_t r = two_stage_run_in_vs(&ctx, test_vs_read_write, target);
    TEST_ASSERT_EQ("VS-mode r/w through 16KB root succeeds", r, 0UL);

    /* Verify hgatp.MODE is active. */
    TEST_ASSERT_EQ("hgatp.MODE active",
                   HGATP_GET_MODE(hgatp_read()),
                   (uintptr_t)SUITE_HGATP_MODE);

    two_stage_cleanup(&ctx);
    hyp_reset_state();
    HYP_TEST_END();
}
