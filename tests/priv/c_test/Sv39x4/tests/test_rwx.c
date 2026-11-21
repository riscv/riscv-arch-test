/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 8: G-stage RWX permissions (GRWX-01..07)
 *
 * Spec anchors:
 *   norm:gstage_perm_check        - leaf RWX bits checked at G-stage
 *   norm:gstage_pte_reserved      - W=1,R=0 reserved (also Group 7)
 *   norm:gstage_walk_intermediate - intermediate (R=W=X=0) means
 *                                   non-leaf (follow pointer)
 *
 * Reuses _setup_with_victim() and _vsfault_check() from test_helpers.c.
 * =================================================================== */

/* GRWX-01: R-only leaf, load succeeds + store -> store gpf */
TEST_REGISTER(test_grwx_01_ronly_store);
bool test_grwx_01_ronly_store(void) {
    TEST_BEGIN("GRWX-01: G-stage R-only leaf -> load ok, store gpf");
    uintptr_t flags = PTE_V | PTE_R | PTE_U | PTE_A | PTE_D;

    /* Verify load succeeds on R-only leaf. */
    two_stage_ctx_t ctx;
    _setup_with_victim(&ctx, (uintptr_t)test_fault_page, flags);
    *(volatile uint64_t *)test_fault_page = 0;
    uintptr_t r = two_stage_run_in_vs(&ctx, test_vs_load,
                                      (uintptr_t)test_fault_page);
    TEST_ASSERT("R-only leaf: load succeeds", r == 0 || r == 0 /* load returns value */);
    two_stage_cleanup(&ctx);
    hyp_reset_state();

    /* Verify store faults on R-only leaf. */
    bool ok = _vsfault_check(test_vs_store_expect_fault,
                             (uintptr_t)test_fault_page,
                             flags, CAUSE_STORE_GUEST_PAGE_FAULT);
    TEST_ASSERT("R-only leaf: store gpf", ok);
    HYP_TEST_END();
}

/* GRWX-02: RW leaf, load/store succeed + exec -> inst gpf */
TEST_REGISTER(test_grwx_02_rw_exec);
bool test_grwx_02_rw_exec(void) {
    TEST_BEGIN("GRWX-02: G-stage RW leaf -> load/store ok, inst gpf on exec");
    uintptr_t flags = PTE_V | PTE_R | PTE_W | PTE_U | PTE_A | PTE_D;

    /* Verify load+store succeed on RW leaf. */
    two_stage_ctx_t ctx;
    _setup_with_victim(&ctx, (uintptr_t)test_fault_page, flags);
    *(volatile uint64_t *)test_fault_page = 0;
    uintptr_t r = two_stage_run_in_vs(&ctx, test_vs_read_write,
                                      (uintptr_t)test_fault_page);
    TEST_ASSERT("RW leaf: load/store succeeds", r == 0);
    two_stage_cleanup(&ctx);
    hyp_reset_state();

    /* Verify exec faults on RW leaf. */
    bool ok = _vsfault_check(test_vs_exec_expect_fault,
                             (uintptr_t)test_fault_page,
                             flags, CAUSE_INST_GUEST_PAGE_FAULT);
    TEST_ASSERT("RW leaf: exec inst gpf", ok);
    HYP_TEST_END();
}

/* GRWX-03: RX leaf, load/fetch succeed + store -> store gpf */
TEST_REGISTER(test_grwx_03_rx_store);
bool test_grwx_03_rx_store(void) {
    TEST_BEGIN("GRWX-03: G-stage RX leaf -> load/fetch ok, store gpf");
    uintptr_t flags = PTE_V | PTE_R | PTE_X | PTE_U | PTE_A | PTE_D;

    /* Verify load succeeds on RX leaf. */
    two_stage_ctx_t ctx;
    _setup_with_victim(&ctx, (uintptr_t)test_fault_page, flags);
    *(volatile uint64_t *)test_fault_page = 0;
    uintptr_t r = two_stage_run_in_vs(&ctx, test_vs_load,
                                      (uintptr_t)test_fault_page);
    TEST_ASSERT("RX leaf: load succeeds", r == 0 || r == 0 /* load returns value */);
    two_stage_cleanup(&ctx);
    hyp_reset_state();

    /* Verify store faults on RX leaf. */
    bool ok = _vsfault_check(test_vs_store_expect_fault,
                             (uintptr_t)test_fault_page,
                             flags, CAUSE_STORE_GUEST_PAGE_FAULT);
    TEST_ASSERT("RX leaf: store gpf", ok);
    HYP_TEST_END();
}

/* GRWX-04: RWX leaf, R+W both succeed */
TEST_REGISTER(test_grwx_04_rwx_ok);
bool test_grwx_04_rwx_ok(void) {
    TEST_BEGIN("GRWX-04: G-stage RWX leaf permits R+W");

    two_stage_ctx_t ctx;
    _setup_with_victim(&ctx, (uintptr_t)test_fault_page,
                       G_FLAGS_RWXU_AD);

    *(volatile uint64_t *)test_fault_page = 0;
    uintptr_t r = two_stage_run_in_vs(&ctx, test_vs_read_write,
                                      (uintptr_t)test_fault_page);
    TEST_ASSERT("VS r/w returns 0 on RWX leaf", r == 0);

    two_stage_cleanup(&ctx);
    HYP_TEST_END();
}

/* GRWX-05: X-only leaf, load -> load gpf (sstatus.MXR=0 default)
 *
 * NOTE: We cannot directly verify "fetch succeeds" on X-only leaf
 * because the fault page contains no valid executable code — the
 * fetch would pass G-stage (X=1) but then hit an illegal-instruction
 * trap from the page content. G-stage fetch permission is implicitly
 * validated by the G-stage translation allowing the access through;
 * explicit fetch-success testing would require a code-bearing page. */
TEST_REGISTER(test_grwx_05_xonly_load);
bool test_grwx_05_xonly_load(void) {
    TEST_BEGIN("GRWX-05: G-stage X-only leaf -> load gpf");
    uintptr_t flags = PTE_V | PTE_X | PTE_U | PTE_A | PTE_D;
    bool ok = _vsfault_check(test_vs_load_expect_fault,
                             (uintptr_t)test_fault_page,
                             flags, CAUSE_LOAD_GUEST_PAGE_FAULT);
    TEST_ASSERT("X-only leaf: load gpf", ok);
    HYP_TEST_END();
}

/* GRWX-06: alias of GVALID-04/05 (W=1,R=0 reserved) */
TEST_REGISTER(test_grwx_06_reserved_alias);
bool test_grwx_06_reserved_alias(void) {
    TEST_BEGIN("GRWX-06: W=1,R=0 reserved (alias)");
    uintptr_t flags = PTE_V | PTE_W | PTE_U | PTE_A | PTE_D;
    bool ok = _vsfault_check(test_vs_store_expect_fault,
                             (uintptr_t)test_fault_page,
                             flags, CAUSE_STORE_GUEST_PAGE_FAULT);
    TEST_ASSERT("W=1,R=0 reserved store -> gpf", ok);
    HYP_TEST_END();
}

/* GRWX-07: intermediate (R=W=X=0, V=1) followed across all levels */
TEST_REGISTER(test_grwx_07_intermediate_followed);
bool test_grwx_07_intermediate_followed(void) {
    TEST_BEGIN("GRWX-07: intermediate PTE followed across levels");

    two_stage_ctx_t ctx;
    _setup_with_victim(&ctx, (uintptr_t)test_fault_page,
                       G_FLAGS_RWXU_AD);

    *(volatile uint64_t *)test_data_area = 0;
    uintptr_t r = two_stage_run_in_vs(&ctx, test_vs_read_write,
                                      (uintptr_t)test_data_area);
    TEST_ASSERT("intermediate walks succeed", r == 0);

    two_stage_cleanup(&ctx);
    HYP_TEST_END();
}
