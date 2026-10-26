/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 9: hstatus.GVA linkage (HTVAL-GVA-*)
 *
 * Spec anchor:
 *   norm:H_hstatus_gva — on guest-page-fault delivered to HS-mode (or
 *   captured in M-mode when hedeleg=0), hstatus.GVA / mstatus.GVA = 1
 *   when the faulting address is virtualized; htval is then valid.
 *
 * Plan list:
 *   HTVAL-GVA-01  load gpf sets GVA=1 alongside htval=GPA>>2
 *   HTVAL-GVA-02  fetch gpf sets GVA=1 alongside htval=GPA>>2
 *   HTVAL-GVA-03  non-GPF trap sets GVA=0 alongside htval=0
 * =================================================================== */

TEST_REGISTER(test_htval_gva_01_load);
bool test_htval_gva_01_load(void) {
    TEST_BEGIN("HTVAL-GVA-01: load gpf sets GVA and writes htval together");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t target = (uintptr_t)test_fault_page;
    uintptr_t flags  = (G_FLAGS_RWXU_AD & ~PTE_R);

    bool fired = fire_vs_load_fault(target, flags);
    TEST_ASSERT("load gpf fired", fired);
    if (fired) {
        TEST_ASSERT("GVA flag is 1",         trap_get_gva());
        TEST_ASSERT_EQ("htval = GPA>>2",     trap_get_htval(), target >> 2);
    }
    hyp_reset_state();
    HYP_TEST_END();
}

TEST_REGISTER(test_htval_gva_02_fetch);
bool test_htval_gva_02_fetch(void) {
    TEST_BEGIN("HTVAL-GVA-02: fetch gpf sets GVA and writes htval together");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t target = (uintptr_t)test_fault_page;
    uintptr_t flags  = (G_FLAGS_RWXU_AD & ~PTE_X);

    bool fired = _fire_fetch_fault(target, flags);
    TEST_ASSERT("fetch gpf fired", fired);
    if (fired) {
        TEST_ASSERT("GVA flag is 1",         trap_get_gva());
        TEST_ASSERT_EQ("htval = GPA>>2",     trap_get_htval(), target >> 2);
    }
    hyp_reset_state();
    HYP_TEST_END();
}

/* VS-mode helper: read HS-level CSR -> virtual-instruction exception. */
static uintptr_t vs_csrr_hstatus_gva(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, " CSR_STR(CSR_HSTATUS) : "=r"(v));   /* hstatus */
    return v;
}

TEST_REGISTER(test_htval_gva_03_non_gpf);
bool test_htval_gva_03_non_gpf(void) {
    TEST_BEGIN("HTVAL-GVA-03: non-GPF trap sets GVA=0 and htval=0");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    /* Trigger a virtual-instruction exception from VS-mode by
     * reading the HS-level CSR hstatus (cause=22). This is a
     * non-GPF trap, so GVA must be 0 and htval must be 0. */
    trap_expect_begin();
    (void)run_in_vs_mode(vs_csrr_hstatus_gva, 0);
    TEST_ASSERT("virtual-inst trap fired", trap_was_triggered());
    trap_expect_end();

    TEST_ASSERT_EQ("cause = 22 (virtual-instruction)",
                   trap_get_cause(), (uintptr_t)CAUSE_VIRTUAL_INSTRUCTION);
    CHECK_GVA("GVA flag is 0", 0);
    TEST_ASSERT_EQ("htval = 0", trap_get_htval(), 0UL);

    hyp_reset_state();
    HYP_TEST_END();
}
