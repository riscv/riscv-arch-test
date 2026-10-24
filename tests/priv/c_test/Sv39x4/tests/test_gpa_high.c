/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 6: GPA high-bit check
 *
 * Spec anchors:
 *   norm:gstage_gpa_width_check - GPA bits above the supported width
 *                                 must be zero, otherwise a
 *                                 guest-page-fault is raised.
 *
 * Sv39x4 (41-bit GPA):
 *   GHIGH-01: VS-mode load from a GPA whose bit 41 is set -> load gpf
 *   GHIGH-02: VS-mode store to  a GPA whose bit 42 is set -> store gpf
 *
 * Sv48x4 (50-bit GPA):
 *   GHIGH-03: VS-mode load from a GPA with bit 50 set   -> load gpf
 *   GHIGH-04: VS-mode store  to a GPA with bit 63 set   -> store gpf
 *
 * Sv57x4 (59-bit GPA):
 *   GHIGH-05: VS-mode load from a GPA with bit 59 set   -> load gpf
 *   GHIGH-06: VS-mode store  to a GPA with bit 63 set   -> store gpf
 *
 * Reuses _setup_with_victim() from test_helpers.c. The victim flags
 * are normal (RWXU|A|D) — the *fault source* is the GPA bit, not
 * the leaf flags.
 * =================================================================== */

#if SUITE_HGATP_MODE == HGATP_MODE_SV39X4

/* GHIGH-01: GPA bit 41 set -> load guest-page-fault */
TEST_REGISTER(test_ghigh_01_load_high_bit);
bool test_ghigh_01_load_high_bit(void) {
    TEST_BEGIN("GHIGH-01: GPA bit 41 set -> load guest-page-fault");

    two_stage_ctx_t ctx;
    _setup_with_victim(&ctx, (uintptr_t)test_data_area, G_FLAGS_RWXU_AD);

    uintptr_t bad_gpa = (uintptr_t)test_data_area | (1UL << 41);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_load_expect_fault, bad_gpa);
    bool fired = trap_was_triggered();
    uintptr_t cause = fired ? trap_get_cause() : 0;
    trap_expect_end();

    TEST_ASSERT("trap triggered", fired);
    if (fired) {
        TEST_ASSERT_EQ("cause = load gpf (21)", cause,
                       (uintptr_t)CAUSE_LOAD_GUEST_PAGE_FAULT);
    }

    two_stage_cleanup(&ctx);
    HYP_TEST_END();
}

/* GHIGH-02: GPA bit 42 set -> store guest-page-fault */
TEST_REGISTER(test_ghigh_02_store_high_bit);
bool test_ghigh_02_store_high_bit(void) {
    TEST_BEGIN("GHIGH-02: GPA bit 42 set -> store guest-page-fault");

    two_stage_ctx_t ctx;
    _setup_with_victim(&ctx, (uintptr_t)test_data_area, G_FLAGS_RWXU_AD);

    uintptr_t bad_gpa = (uintptr_t)test_data_area | (1UL << 42);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_store_expect_fault, bad_gpa);
    bool fired = trap_was_triggered();
    uintptr_t cause = fired ? trap_get_cause() : 0;
    trap_expect_end();

    TEST_ASSERT("trap triggered", fired);
    if (fired) {
        TEST_ASSERT_EQ("cause = store gpf (23)", cause,
                       (uintptr_t)CAUSE_STORE_GUEST_PAGE_FAULT);
    }

    two_stage_cleanup(&ctx);
    HYP_TEST_END();
}

#elif SUITE_HGATP_MODE == HGATP_MODE_SV48X4

/* GHIGH-03: GPA bit 50 set -> load guest-page-fault */
TEST_REGISTER(test_ghigh_03_load_bit50);
bool test_ghigh_03_load_bit50(void) {
    TEST_BEGIN("GHIGH-03: Sv48x4 GPA bit 50 set -> load guest-page-fault");

    two_stage_ctx_t ctx;
    _setup_with_victim(&ctx, (uintptr_t)test_data_area, G_FLAGS_RWXU_AD);

    uintptr_t bad_gpa = (uintptr_t)test_data_area | (1UL << 50);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_load_expect_fault, bad_gpa);
    bool fired = trap_was_triggered();
    uintptr_t cause = fired ? trap_get_cause() : 0;
    trap_expect_end();

    TEST_ASSERT("trap triggered", fired);
    if (fired) {
        TEST_ASSERT_EQ("cause = load gpf (21)", cause,
                       (uintptr_t)CAUSE_LOAD_GUEST_PAGE_FAULT);
    }

    two_stage_cleanup(&ctx);
    HYP_TEST_END();
}

/* GHIGH-04: GPA bit 63 set -> store guest-page-fault */
TEST_REGISTER(test_ghigh_04_store_bit63);
bool test_ghigh_04_store_bit63(void) {
    TEST_BEGIN("GHIGH-04: Sv48x4 GPA bit 63 set -> store guest-page-fault");

    two_stage_ctx_t ctx;
    _setup_with_victim(&ctx, (uintptr_t)test_data_area, G_FLAGS_RWXU_AD);

    uintptr_t bad_gpa = (uintptr_t)test_data_area | (1UL << 63);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_store_expect_fault, bad_gpa);
    bool fired = trap_was_triggered();
    uintptr_t cause = fired ? trap_get_cause() : 0;
    trap_expect_end();

    TEST_ASSERT("trap triggered", fired);
    if (fired) {
        TEST_ASSERT_EQ("cause = store gpf (23)", cause,
                       (uintptr_t)CAUSE_STORE_GUEST_PAGE_FAULT);
    }

    two_stage_cleanup(&ctx);
    HYP_TEST_END();
}

#elif SUITE_HGATP_MODE == HGATP_MODE_SV57X4

/* GHIGH-05: GPA bit 59 set -> load guest-page-fault */
TEST_REGISTER(test_ghigh_05_load_bit59);
bool test_ghigh_05_load_bit59(void) {
    TEST_BEGIN("GHIGH-05: Sv57x4 GPA bit 59 set -> load guest-page-fault");

    two_stage_ctx_t ctx;
    _setup_with_victim(&ctx, (uintptr_t)test_data_area, G_FLAGS_RWXU_AD);

    uintptr_t bad_gpa = (uintptr_t)test_data_area | (1UL << 59);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_load_expect_fault, bad_gpa);
    bool fired = trap_was_triggered();
    uintptr_t cause = fired ? trap_get_cause() : 0;
    trap_expect_end();

    TEST_ASSERT("trap triggered", fired);
    if (fired) {
        TEST_ASSERT_EQ("cause = load gpf (21)", cause,
                       (uintptr_t)CAUSE_LOAD_GUEST_PAGE_FAULT);
    }

    two_stage_cleanup(&ctx);
    HYP_TEST_END();
}

/* GHIGH-06: GPA bit 63 set -> store guest-page-fault */
TEST_REGISTER(test_ghigh_06_store_bit63);
bool test_ghigh_06_store_bit63(void) {
    TEST_BEGIN("GHIGH-06: Sv57x4 GPA bit 63 set -> store guest-page-fault");

    two_stage_ctx_t ctx;
    _setup_with_victim(&ctx, (uintptr_t)test_data_area, G_FLAGS_RWXU_AD);

    uintptr_t bad_gpa = (uintptr_t)test_data_area | (1UL << 63);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_store_expect_fault, bad_gpa);
    bool fired = trap_was_triggered();
    uintptr_t cause = fired ? trap_get_cause() : 0;
    trap_expect_end();

    TEST_ASSERT("trap triggered", fired);
    if (fired) {
        TEST_ASSERT_EQ("cause = store gpf (23)", cause,
                       (uintptr_t)CAUSE_STORE_GUEST_PAGE_FAULT);
    }

    two_stage_cleanup(&ctx);
    HYP_TEST_END();
}

#endif /* SUITE_HGATP_MODE */
