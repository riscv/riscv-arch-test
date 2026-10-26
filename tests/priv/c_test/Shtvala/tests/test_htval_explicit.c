/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 2: Explicit G-stage GPF — htval = GPA >> 2
 *
 * Spec anchor:
 *   norm:H_htval — on guest-page-fault, htval = faulting GPA >> 2.
 *
 * Each test forces a single G-stage permission/V-bit fault on a
 * known 4KB GPA, then inspects htval/scause to verify both the
 * cause code and htval value.
 *
 *   HTVAL-LGP-01  load gpf  on R=0 page    -> cause=21, htval=GPA>>2
 *   HTVAL-LGP-02  load gpf  on V=0 page    -> cause=21, htval=GPA>>2
 *   HTVAL-SGP-01  store gpf on W=0 page    -> cause=23, htval=GPA>>2
 *   HTVAL-SGP-02  store gpf on V=0 page    -> cause=23, htval=GPA>>2
 *   HTVAL-IGP-01  fetch gpf on X=0 page    -> cause=20, htval=GPA>>2
 *   HTVAL-IGP-02  fetch gpf on V=0 page    -> cause=20, htval=GPA>>2
 *
 * Uses _fire_*_fault() helpers from test_helpers.c which keep
 * trap_record alive across the trap_expect_end() boundary.
 * =================================================================== */

/* ---- HTVAL-LGP : load guest-page-fault ----------------------------- */

TEST_REGISTER(test_htval_lgp_01_load_perm);
bool test_htval_lgp_01_load_perm(void) {
    TEST_BEGIN("HTVAL-LGP-01: load gpf (R=0) reports htval = GPA>>2");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t target = (uintptr_t)test_fault_page;
    uintptr_t flags  = (G_FLAGS_RWXU_AD & ~PTE_R);

    bool fired = fire_vs_load_fault(target, flags);
    TEST_ASSERT("load gpf fired", fired);
    if (fired) {
        TEST_ASSERT_EQ("cause = 21",  trap_get_cause(), CAUSE_LOAD_GUEST_PAGE_FAULT);
        TEST_ASSERT_EQ("htval = GPA>>2", trap_get_htval(), target >> 2);
    }
    hyp_reset_state();
    HYP_TEST_END();
}

TEST_REGISTER(test_htval_lgp_02_load_invalid);
bool test_htval_lgp_02_load_invalid(void) {
    TEST_BEGIN("HTVAL-LGP-02: load gpf (V=0) reports htval = GPA>>2");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t target = (uintptr_t)test_fault_page;
    uintptr_t flags  = 0;  /* V=0 */

    bool fired = fire_vs_load_fault(target, flags);
    TEST_ASSERT("load gpf fired", fired);
    if (fired) {
        TEST_ASSERT_EQ("cause = 21",  trap_get_cause(), CAUSE_LOAD_GUEST_PAGE_FAULT);
        TEST_ASSERT_EQ("htval = GPA>>2", trap_get_htval(), target >> 2);
    }
    hyp_reset_state();
    HYP_TEST_END();
}

/* ---- HTVAL-SGP : store guest-page-fault ---------------------------- */

TEST_REGISTER(test_htval_sgp_01_store_perm);
bool test_htval_sgp_01_store_perm(void) {
    TEST_BEGIN("HTVAL-SGP-01: store gpf (W=0) reports htval = GPA>>2");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t target = (uintptr_t)test_fault_page;
    uintptr_t flags  = (G_FLAGS_RWXU_AD & ~PTE_W);

    bool fired = fire_vs_store_fault(target, flags);
    TEST_ASSERT("store gpf fired", fired);
    if (fired) {
        TEST_ASSERT_EQ("cause = 23",  trap_get_cause(), CAUSE_STORE_GUEST_PAGE_FAULT);
        TEST_ASSERT_EQ("htval = GPA>>2", trap_get_htval(), target >> 2);
    }
    hyp_reset_state();
    HYP_TEST_END();
}

TEST_REGISTER(test_htval_sgp_02_store_invalid);
bool test_htval_sgp_02_store_invalid(void) {
    TEST_BEGIN("HTVAL-SGP-02: store gpf (V=0) reports htval = GPA>>2");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t target = (uintptr_t)test_fault_page;
    uintptr_t flags  = 0;

    bool fired = fire_vs_store_fault(target, flags);
    TEST_ASSERT("store gpf fired", fired);
    if (fired) {
        TEST_ASSERT_EQ("cause = 23",  trap_get_cause(), CAUSE_STORE_GUEST_PAGE_FAULT);
        TEST_ASSERT_EQ("htval = GPA>>2", trap_get_htval(), target >> 2);
    }
    hyp_reset_state();
    HYP_TEST_END();
}

/* ---- HTVAL-LGP-03 : two-stage load guest-page-fault --------------- */

/* test_gva lives in a different VPN[2] region from kernel so that
 * VS-stage creates separate page tables, and we can independently
 * control the G-stage mapping of test_gpa. */
#define LGP03_TEST_GVA  0x40000000UL

TEST_REGISTER(test_htval_lgp_03_two_stage);
bool test_htval_lgp_03_two_stage(void) {
    TEST_BEGIN("HTVAL-LGP-03: load gpf after VS-stage translation, htval = GPA>>2");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    /* test_gpa = test_fault_page's physical address (= GPA under identity map). */
    uintptr_t test_gpa = (uintptr_t)test_fault_page;

    /* vsatp=Sv39: LGP03_TEST_GVA -> test_gpa (full VS perms).
     * hgatp=Sv39x4: test_gpa page is Invalid (V=0).
     * VS-mode load from LGP03_TEST_GVA -> VS-stage translates to test_gpa
     * -> G-stage lookup fails (V=0) -> load GPF (cause=21). */
    bool fired = _fire_two_stage_load_fault(LGP03_TEST_GVA, test_gpa,
                                            /*victim_flags=*/0);
    TEST_ASSERT("two-stage load gpf fired", fired);
    if (fired) {
        TEST_ASSERT_EQ("cause = 21",
                       trap_get_cause(), CAUSE_LOAD_GUEST_PAGE_FAULT);
        /* htval must be the G-stage faulting GPA >> 2, NOT the GVA */
        TEST_ASSERT_EQ("htval = GPA>>2 (not GVA>>2)",
                       trap_get_htval(), test_gpa >> 2);
        /* Verify tval reports the original GVA (not GPA) */
        TEST_ASSERT_EQ("tval = GVA",
                       trap_get_tval(), LGP03_TEST_GVA);
    }
    hyp_reset_state();
    HYP_TEST_END();
}

/* ---- HTVAL-SGP-02 : store GPF with A=1, D=0 ---------------------- */

TEST_REGISTER(test_htval_sgp_02_store_ad);
bool test_htval_sgp_02_store_ad(void) {
    TEST_BEGIN("HTVAL-SGP-02: store gpf (A=1,D=0) reports htval = GPA>>2");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t target = (uintptr_t)test_fault_page;
    /* V=1, R=1, W=1, X=1, U=1, A=1, D=0.
     * Without Svadu, a store must fault because D=0. */
    uintptr_t flags  = (G_FLAGS_RWXU_AD & ~PTE_D);

    bool fired = fire_vs_store_fault(target, flags);
    if (!fired) {
        /* Platform has Svadu (auto-updates D bit) — no fault fires. */
        LOG_W("platform auto-updates D bit (Svadu), no GPF\n");
        TEST_SKIP("Svadu prevents D=0 store GPF");
    }
    TEST_ASSERT_EQ("cause = 23",
                   trap_get_cause(), CAUSE_STORE_GUEST_PAGE_FAULT);
    TEST_ASSERT_EQ("htval = GPA>>2",
                   trap_get_htval(), target >> 2);
    hyp_reset_state();
    HYP_TEST_END();
}

/* ---- HTVAL-AMO-01 : AMO store guest-page-fault -------------------- */

TEST_REGISTER(test_htval_amo_01_store_gpf);
bool test_htval_amo_01_store_gpf(void) {
    TEST_BEGIN("HTVAL-AMO-01: AMO gpf (W=0) reports htval = GPA>>2");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t target = (uintptr_t)test_fault_page;
    /* AMO requires both R and W. Remove W to trigger store GPF. */
    uintptr_t flags  = (G_FLAGS_RWXU_AD & ~PTE_W);

    bool fired = _fire_amo_fault(target, flags);
    TEST_ASSERT("AMO store-gpf fired", fired);
    if (fired) {
        TEST_ASSERT_EQ("cause = 23 (store/AMO gpf)",
                       trap_get_cause(), CAUSE_STORE_GUEST_PAGE_FAULT);
        TEST_ASSERT_EQ("htval = GPA>>2",
                       trap_get_htval(), target >> 2);
    }
    hyp_reset_state();
    HYP_TEST_END();
}

TEST_REGISTER(test_htval_igp_01_fetch_perm);
bool test_htval_igp_01_fetch_perm(void) {
    TEST_BEGIN("HTVAL-IGP-01: fetch gpf (X=0) reports htval = GPA>>2");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t target = (uintptr_t)test_fault_page;
    uintptr_t flags  = (G_FLAGS_RWXU_AD & ~PTE_X);

    bool fired = _fire_fetch_fault(target, flags);
    TEST_ASSERT("fetch gpf fired", fired);
    if (fired) {
        TEST_ASSERT_EQ("cause = 20",  trap_get_cause(), CAUSE_INST_GUEST_PAGE_FAULT);
        TEST_ASSERT_EQ("htval = GPA>>2", trap_get_htval(), target >> 2);
    }
    hyp_reset_state();
    HYP_TEST_END();
}

TEST_REGISTER(test_htval_igp_02_fetch_invalid);
bool test_htval_igp_02_fetch_invalid(void) {
    TEST_BEGIN("HTVAL-IGP-02: fetch gpf (V=0) reports htval = GPA>>2");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t target = (uintptr_t)test_fault_page;
    uintptr_t flags  = 0;

    bool fired = _fire_fetch_fault(target, flags);
    TEST_ASSERT("fetch gpf fired", fired);
    if (fired) {
        TEST_ASSERT_EQ("cause = 20",  trap_get_cause(), CAUSE_INST_GUEST_PAGE_FAULT);
        TEST_ASSERT_EQ("htval = GPA>>2", trap_get_htval(), target >> 2);
    }
    hyp_reset_state();
    HYP_TEST_END();
}
