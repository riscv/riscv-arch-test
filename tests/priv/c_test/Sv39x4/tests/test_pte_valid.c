/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 7: G-stage PTE validity (GVALID-01..05)
 *
 * Spec anchors:
 *   norm:gstage_pte_v_zero   - PTE.V=0 -> guest-page-fault
 *   norm:gstage_pte_reserved - R=0 && W=1 reserved encoding -> gpf
 *   norm:gpf_cause_codes     - load=21, store=23, fetch=20
 *
 * GVALID-01: load via V=0 leaf  -> cause 21
 * GVALID-02: store via V=0 leaf -> cause 23
 * GVALID-03: fetch via V=0 leaf -> cause 20
 * GVALID-04: load via R=0,W=1   -> cause 21 (reserved encoding)
 * GVALID-05: store via R=0,W=1  -> cause 23 (reserved encoding)
 *
 * NOTE: _setup_with_victim() and _vsfault_check() are defined in
 * test_helpers.c (extracted to break implicit include-order coupling
 * between Group test files).
 * =================================================================== */

/* GVALID-01: load via V=0 leaf -> cause 21 */
TEST_REGISTER(test_gvalid_01_v0_load);
bool test_gvalid_01_v0_load(void) {
    TEST_BEGIN("GVALID-01: load via V=0 leaf -> cause 21");

    /* V cleared, U set so failure is purely from V=0. */
    uintptr_t flags = (G_FLAGS_RWXU_AD & ~PTE_V);
    bool ok = _vsfault_check(test_vs_load_expect_fault,
                             (uintptr_t)test_fault_page,
                             flags, CAUSE_LOAD_GUEST_PAGE_FAULT);
    TEST_ASSERT("V=0 load fault", ok);
    HYP_TEST_END();
}

/* GVALID-02: store via V=0 leaf -> cause 23 */
TEST_REGISTER(test_gvalid_02_v0_store);
bool test_gvalid_02_v0_store(void) {
    TEST_BEGIN("GVALID-02: store via V=0 leaf -> cause 23");

    uintptr_t flags = (G_FLAGS_RWXU_AD & ~PTE_V);
    bool ok = _vsfault_check(test_vs_store_expect_fault,
                             (uintptr_t)test_fault_page,
                             flags, CAUSE_STORE_GUEST_PAGE_FAULT);
    TEST_ASSERT("V=0 store fault", ok);
    HYP_TEST_END();
}

/* GVALID-03: fetch via V=0 leaf -> cause 20 */
TEST_REGISTER(test_gvalid_03_v0_fetch);
bool test_gvalid_03_v0_fetch(void) {
    TEST_BEGIN("GVALID-03: fetch via V=0 leaf -> cause 20");

    uintptr_t flags = (G_FLAGS_RWXU_AD & ~PTE_V);
    bool ok = _vsfault_check(test_vs_exec_expect_fault,
                             (uintptr_t)test_fault_page,
                             flags, CAUSE_INST_GUEST_PAGE_FAULT);
    TEST_ASSERT("V=0 fetch fault", ok);
    HYP_TEST_END();
}

/* GVALID-04: load via reserved R=0,W=1 -> cause 21 */
TEST_REGISTER(test_gvalid_04_rsvd_load);
bool test_gvalid_04_rsvd_load(void) {
    TEST_BEGIN("GVALID-04: R=0,W=1 reserved load -> cause 21");

    uintptr_t flags = PTE_V | PTE_W | PTE_U | PTE_A | PTE_D;
    bool ok = _vsfault_check(test_vs_load_expect_fault,
                             (uintptr_t)test_fault_page,
                             flags, CAUSE_LOAD_GUEST_PAGE_FAULT);
    TEST_ASSERT("R=0,W=1 load fault", ok);
    HYP_TEST_END();
}

/* GVALID-05: store via reserved R=0,W=1 -> cause 23 */
TEST_REGISTER(test_gvalid_05_rsvd_store);
bool test_gvalid_05_rsvd_store(void) {
    TEST_BEGIN("GVALID-05: R=0,W=1 reserved store -> cause 23");

    uintptr_t flags = PTE_V | PTE_W | PTE_U | PTE_A | PTE_D;
    bool ok = _vsfault_check(test_vs_store_expect_fault,
                             (uintptr_t)test_fault_page,
                             flags, CAUSE_STORE_GUEST_PAGE_FAULT);
    TEST_ASSERT("R=0,W=1 store fault", ok);
    HYP_TEST_END();
}
