/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_misaligned.c - Group 3: Misaligned Address Exceptions
 *
 * Tests VSTVAL-IMA-01, VSTVAL-LMA-01, VSTVAL-SMA-01
 *
 * Validates that when a misaligned exception is delegated to VS-mode,
 * vstval is written with the faulting (unaligned) virtual address.
 *
 * Note: LMA/SMA tests may be skipped on platforms with hardware
 * misaligned access support.
 */

/* ------------------------------------------------------------------ */
/* VSTVAL-IMA-01: instruction address misaligned (jump to odd addr)   */
/* ------------------------------------------------------------------ */
TEST_REGISTER(test_shvstvala_ima_01);
bool test_shvstvala_ima_01(void) {
    TEST_BEGIN("VSTVAL-IMA-01: instruction misaligned vstval == faulting addr");

    /* With C extension (IALIGN=16), JALR clears bit 0 of target address,
     * making it always 2-byte aligned. Instruction-address-misaligned is
     * impossible in this configuration. C availability is a build property of
     * the -march this suite is compiled for (capabilities.h): misa is M-level
     * and cannot be read from the S(HS)-mode the suite body runs in. */
    if (C_AVAILABLE) {  /* C extension present */
        TEST_SKIP("C extension present: JALR always clears bit 0, "
                  "instruction misaligned impossible");
    }

    /* Delegate instruction address misaligned (cause=0) to VS-mode */
    hyp_delegate_to_vs((1UL << 0), 0);

    g_shvstvala_vstval = 0;
    g_shvstvala_cause  = ~0UL;

    /* Two-stage identity map for VS-mode execution */
    two_stage_ctx_t ctx;
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    /* Without C extension, IALIGN=32. Jump target with bit 1 set
     * (but bit 0 cleared by JALR) gives a 2-byte aligned address
     * that is not 4-byte aligned -> instruction misaligned. */
    uintptr_t target = ((uintptr_t)test_exec_page) | 0x2UL;

    two_stage_run_in_vs(&ctx, vsmode_jump_misaligned, target);

    TEST_ASSERT_EQ("vscause == instruction address misaligned (0)",
                   g_shvstvala_cause, (uintptr_t)0);
    TEST_ASSERT_EQ("vstval == misaligned target address",
                   g_shvstvala_vstval, target);

    two_stage_cleanup(&ctx);
    hyp_undelegate();
    HYP_TEST_END();
}

/* ------------------------------------------------------------------ */
/* VSTVAL-LMA-01: load address misaligned                             */
/* ------------------------------------------------------------------ */
TEST_REGISTER(test_shvstvala_lma_01);
bool test_shvstvala_lma_01(void) {
    TEST_BEGIN("VSTVAL-LMA-01: load misaligned vstval == faulting addr");

    /* Delegate load address misaligned (cause=4) to VS-mode */
    hyp_delegate_to_vs((1UL << 4), 0);

    g_shvstvala_vstval = 0;
    g_shvstvala_cause  = ~0UL;

    /* Two-stage identity map */
    two_stage_ctx_t ctx;
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    /* Misaligned address: base + 3 (not 8-byte aligned for ld) */
    uintptr_t misaligned_addr = ((uintptr_t)test_data_area) + 3;

    two_stage_run_in_vs(&ctx, vsmode_load_misaligned, misaligned_addr);

    /* If platform supports hardware misaligned load, no trap occurs */
    if (g_shvstvala_cause == ~0UL) {
        two_stage_cleanup(&ctx);
        hyp_undelegate();
        TEST_SKIP("platform supports hardware misaligned load");
    }

    TEST_ASSERT_EQ("vscause == load address misaligned (4)",
                   g_shvstvala_cause, (uintptr_t)4);
    TEST_ASSERT_EQ("vstval == misaligned address",
                   g_shvstvala_vstval, misaligned_addr);

    two_stage_cleanup(&ctx);
    hyp_undelegate();
    HYP_TEST_END();
}

/* ------------------------------------------------------------------ */
/* VSTVAL-SMA-01: store address misaligned                            */
/* ------------------------------------------------------------------ */
TEST_REGISTER(test_shvstvala_sma_01);
bool test_shvstvala_sma_01(void) {
    TEST_BEGIN("VSTVAL-SMA-01: store misaligned vstval == faulting addr");

    /* Delegate store address misaligned (cause=6) to VS-mode */
    hyp_delegate_to_vs((1UL << 6), 0);

    g_shvstvala_vstval = 0;
    g_shvstvala_cause  = ~0UL;

    /* Two-stage identity map */
    two_stage_ctx_t ctx;
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    /* Misaligned address: base + 5 (not 8-byte aligned for sd) */
    uintptr_t misaligned_addr = ((uintptr_t)test_data_area) + 5;

    two_stage_run_in_vs(&ctx, vsmode_store_misaligned, misaligned_addr);

    /* If platform supports hardware misaligned store, no trap occurs */
    if (g_shvstvala_cause == ~0UL) {
        two_stage_cleanup(&ctx);
        hyp_undelegate();
        TEST_SKIP("platform supports hardware misaligned store");
    }

    TEST_ASSERT_EQ("vscause == store address misaligned (6)",
                   g_shvstvala_cause, (uintptr_t)6);
    TEST_ASSERT_EQ("vstval == misaligned address",
                   g_shvstvala_vstval, misaligned_addr);

    two_stage_cleanup(&ctx);
    hyp_undelegate();
    HYP_TEST_END();
}
