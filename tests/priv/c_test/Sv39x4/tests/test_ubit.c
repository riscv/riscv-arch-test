/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 9: G-stage U-bit always treated as U-mode (GUBIT-01..05)
 *
 * Spec anchors:
 *   norm:H_vm_gpapriv  - All G-stage accesses are U-mode regardless
 *                        of the host privilege mode. So:
 *                        - U=0 G-stage leaf  -> guest-page-fault
 *                        - U=1 G-stage leaf  -> permitted
 *
 * GUBIT-01: VS-mode load via U=0  -> load gpf  (cause 21)
 * GUBIT-02: VS-mode store via U=0 -> store gpf (cause 23)
 * GUBIT-03: VS-mode fetch via U=0 -> inst gpf  (cause 20)
 * GUBIT-04: VU-mode access via U=1 -> success (no fault)
 * GUBIT-05: VS-mode access via U=1 -> success (no fault)
 *
 * Reuses _setup_with_victim() / _vsfault_check() from test_helpers.c.
 * =================================================================== */

/* GUBIT-01: U=0 leaf, VS-mode load -> load gpf */
TEST_REGISTER(test_gubit_01_u0_load);
bool test_gubit_01_u0_load(void) {
    TEST_BEGIN("GUBIT-01: U=0 G-stage leaf -> VS-mode load gpf");
    /* RWX present, A/D set, but U=0 */
    uintptr_t flags = PTE_V | PTE_R | PTE_W | PTE_X | PTE_A | PTE_D;
    bool ok = _vsfault_check(test_vs_load_expect_fault,
                             (uintptr_t)test_fault_page,
                             flags, CAUSE_LOAD_GUEST_PAGE_FAULT);
    TEST_ASSERT("U=0 leaf load -> guest-page-fault", ok);
    HYP_TEST_END();
}

/* GUBIT-02: U=0 leaf, VS-mode store -> store gpf */
TEST_REGISTER(test_gubit_02_u0_store);
bool test_gubit_02_u0_store(void) {
    TEST_BEGIN("GUBIT-02: U=0 G-stage leaf -> VS-mode store gpf");
    uintptr_t flags = PTE_V | PTE_R | PTE_W | PTE_X | PTE_A | PTE_D;
    bool ok = _vsfault_check(test_vs_store_expect_fault,
                             (uintptr_t)test_fault_page,
                             flags, CAUSE_STORE_GUEST_PAGE_FAULT);
    TEST_ASSERT("U=0 leaf store -> guest-page-fault", ok);
    HYP_TEST_END();
}

/* GUBIT-03: U=0 leaf, VS-mode fetch -> inst gpf */
TEST_REGISTER(test_gubit_03_u0_fetch);
bool test_gubit_03_u0_fetch(void) {
    TEST_BEGIN("GUBIT-03: U=0 G-stage leaf -> VS-mode fetch gpf");
    uintptr_t flags = PTE_V | PTE_R | PTE_W | PTE_X | PTE_A | PTE_D;
    bool ok = _vsfault_check(test_vs_exec_expect_fault,
                             (uintptr_t)test_fault_page,
                             flags, CAUSE_INST_GUEST_PAGE_FAULT);
    TEST_ASSERT("U=0 leaf fetch -> guest-page-fault", ok);
    HYP_TEST_END();
}

/* GUBIT-04: U=1 leaf, VU-mode access -> success
 *
 * Sets up a normal RWXU mapping and runs test_vs_read_write inside
 * VU-mode via two_stage_run_in_vu(). Because all G-stage accesses
 * are checked as U-mode and U=1, this should complete without fault.
 * The VS-stage is Bare so VU-mode sees GVA = GPA directly. */
TEST_REGISTER(test_gubit_04_u1_vu_ok);
bool test_gubit_04_u1_vu_ok(void) {
    TEST_BEGIN("GUBIT-04: U=1 G-stage leaf permits VU-mode access");

    two_stage_ctx_t ctx;
    _setup_with_victim(&ctx, (uintptr_t)test_fault_page, G_FLAGS_RWXU_AD);

    /* Pre-zero the target so read_write magic-roundtrip is clean. */
    *(volatile uint64_t *)test_fault_page = 0;

    /* Use two_stage_run_in_vu to actually enter VU-mode (V=1, U).
     * G-stage treats all accesses as U-mode (norm:H_vm_gpapriv),
     * and U=1 in the G-stage PTE permits U-mode access. */
    uintptr_t r = two_stage_run_in_vu(&ctx, test_vs_read_write,
                                      (uintptr_t)test_fault_page);
    TEST_ASSERT("U=1 leaf VU-mode r/w returns 0", r == 0);

    two_stage_cleanup(&ctx);
    hyp_reset_state();
    HYP_TEST_END();
}

/* GUBIT-05: U=1 leaf, VS-mode access -> success */
TEST_REGISTER(test_gubit_05_u1_vs_ok);
bool test_gubit_05_u1_vs_ok(void) {
    TEST_BEGIN("GUBIT-05: U=1 G-stage leaf permits VS-mode access");

    two_stage_ctx_t ctx;
    _setup_with_victim(&ctx, (uintptr_t)test_fault_page, G_FLAGS_RWXU_AD);

    *(volatile uint64_t *)test_fault_page = 0;

    uintptr_t r = two_stage_run_in_vs(&ctx, test_vs_read_write,
                                      (uintptr_t)test_fault_page);
    TEST_ASSERT("U=1 leaf VS-mode r/w returns 0", r == 0);

    two_stage_cleanup(&ctx);
    HYP_TEST_END();
}
