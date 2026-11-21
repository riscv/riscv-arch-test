/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 10: G-stage A/D bit management (GAD-01..04)
 *
 * Spec anchors (corrected after diagnosis, see
 * docs/gad_diagnose_report.md):
 *
 *   norm:menvcfg_adue_op (machine.adoc):
 *     "When the hypervisor extension is implemented, if ADUE=1,
 *      hardware updating of PTE A/D bits is enabled during G-stage
 *      address translation ...
 *      When ADUE=0, the implementation behaves as though Svade were
 *      implemented for S-mode and G-stage address translation."
 *
 *   norm:Svadu_disabled_hw_update_falls_back_to_svade (svadu.adoc):
 *     "When hardware updating of A/D bits is disabled, the Svade
 *      extension, which MANDATES exceptions when A/D bits need be
 *      set, instead takes effect."
 *
 *   svade (supervisor.adoc): "when a virtual page is accessed and
 *     the A bit is clear, or is written and the D bit is clear,
 *     a page-fault exception IS RAISED."
 *
 * IMPORTANT:
 *   - G-stage A/D behavior is controlled by `menvcfg.ADUE`, NOT
 *     `henvcfg.ADUE` (the latter only governs VS-stage).
 *   - The fault behavior is MANDATED (not "may") whenever
 *     `menvcfg.ADUE=0`.
 *   - On QEMU 8.2.94 `-cpu rv64,h=true`, `menvcfg.ADUE` resets to 1
 *     (Svadu enabled by default), so these tests REQUIRE the
 *     reset/init path to explicitly clear `menvcfg.ADUE` before the
 *     fault is observable. See `hyp_reset_state()` in
 *     common/hyp/hyp_reset.c.
 *
 * GAD-01: A=0, load   -> load gpf  (cause 21)
 * GAD-02: A=0, store  -> store gpf (cause 23)
 * GAD-03: D=0, store  -> store gpf (cause 23)  [A=1, D=0]
 * GAD-04: A=1 D=1, load+store both succeed
 *
 * Reuses _setup_with_victim() / _vsfault_check() from test_helpers.c.
 * =================================================================== */

/* GAD-01: A=0, load -> load gpf */
TEST_REGISTER(test_gad_01_a0_load);
bool test_gad_01_a0_load(void) {
    TEST_BEGIN("GAD-01: A=0 G-stage leaf -> load gpf");
    uintptr_t flags = PTE_V | PTE_R | PTE_W | PTE_X | PTE_U | PTE_D;
    bool ok = _vsfault_check(test_vs_load_expect_fault,
                             (uintptr_t)test_fault_page,
                             flags, CAUSE_LOAD_GUEST_PAGE_FAULT);
    TEST_ASSERT("A=0 leaf load -> guest-page-fault", ok);
    HYP_TEST_END();
}

/* GAD-02: A=0, store -> store gpf */
TEST_REGISTER(test_gad_02_a0_store);
bool test_gad_02_a0_store(void) {
    TEST_BEGIN("GAD-02: A=0 G-stage leaf -> store gpf");
    uintptr_t flags = PTE_V | PTE_R | PTE_W | PTE_X | PTE_U | PTE_D;
    bool ok = _vsfault_check(test_vs_store_expect_fault,
                             (uintptr_t)test_fault_page,
                             flags, CAUSE_STORE_GUEST_PAGE_FAULT);
    TEST_ASSERT("A=0 leaf store -> guest-page-fault", ok);
    HYP_TEST_END();
}

/* GAD-03: A=1, D=0, store -> store gpf */
TEST_REGISTER(test_gad_03_d0_store);
bool test_gad_03_d0_store(void) {
    TEST_BEGIN("GAD-03: D=0 G-stage leaf -> store gpf");
    uintptr_t flags = PTE_V | PTE_R | PTE_W | PTE_X | PTE_U | PTE_A;
    bool ok = _vsfault_check(test_vs_store_expect_fault,
                             (uintptr_t)test_fault_page,
                             flags, CAUSE_STORE_GUEST_PAGE_FAULT);
    TEST_ASSERT("D=0 leaf store -> guest-page-fault", ok);
    HYP_TEST_END();
}

/* GAD-04: A=1, D=1 leaf, load+store both succeed */
TEST_REGISTER(test_gad_04_ad_ok);
bool test_gad_04_ad_ok(void) {
    TEST_BEGIN("GAD-04: A=1,D=1 G-stage leaf permits load+store");

    two_stage_ctx_t ctx;
    _setup_with_victim(&ctx, (uintptr_t)test_fault_page, G_FLAGS_RWXU_AD);

    *(volatile uint64_t *)test_fault_page = 0;
    uintptr_t r = two_stage_run_in_vs(&ctx, test_vs_read_write,
                                      (uintptr_t)test_fault_page);
    TEST_ASSERT("A=1,D=1 r/w returns 0", r == 0);

    two_stage_cleanup(&ctx);
    HYP_TEST_END();
}
