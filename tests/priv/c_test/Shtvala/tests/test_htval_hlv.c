/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 5: HLV/HLVX/HSV from HS-mode (V=0) hitting G-stage
 *          (HTVAL-HLV-*)
 *
 * Spec anchors:
 *   norm:hlsv_trans  — HLV/HLVX/HSV always do two-stage translation
 *   norm:htval_trapval / norm:mtval2_trapval — GPF writes GPA>>2
 *   hypervisor.adoc:1505-1507 (NOTE) — HLVX raises load exceptions,
 *       not fetch exceptions
 *
 * When HLV/HSV execute in HS-mode (V=0), the resulting GPF traps
 * to M-mode.  Therefore we verify mcause and mtval2 (not scause /
 * htval).  The framework's trap_get_cause() / trap_get_htval()
 * already return the M-mode values when the trap is taken there.
 *
 * Test list:
 *   HTVAL-HLV-01a HLVX.WU @ VU (SPVP=0) -> cause=21, mtval2=GPA>>2
 *   HTVAL-HLV-01b HLVX.WU @ VS (SPVP=1) -> cause=21, mtval2=GPA>>2
 *   HTVAL-HLV-02  HLV.D    -> cause=21 (load-gpf),  mtval2=GPA>>2
 *   HTVAL-HLV-03  HSV.D    -> cause=23 (store-gpf), mtval2=GPA>>2
 *   HTVAL-HLV-04  HLVX.WU (vsatp=BARE) -> cause=21, mtval2=GPA>>2
 *
 * Implementation notes:
 *   - HLV/HLVX/HSV are valid in M-mode and HS-mode.
 *   - HLV/HSV use vsatp=BARE so the address is a GPA directly.
 *   - HLVX uses vsatp=Sv39 with identity-mapped VS-stage so that
 *     the DUT can deterministically trigger G-stage load-gpf (cause=21).
 *   - The effective privilege is controlled by hstatus.SPVP:
 *     SPVP=0 -> VU (VS PTE needs U=1), SPVP=1 -> VS (VS PTE U=0).
 *   - Per SPEC hypervisor.adoc:1505-1507, HLVX raises the same
 *     exceptions as other *load* instructions — cause=21 (load GPF),
 *     NOT cause=20 (inst GPF).
 *   - The M-mode trap handler captures mtval2 (GPA>>2) into the
 *     trap record; trap_get_htval() returns this value.
 *   - Normal M-mode code/data accesses are NOT subject to G-stage,
 *     so printf/stack/etc. work normally while hgatp is active.
 * =================================================================== */

TEST_REGISTER(test_htval_hlv_01a_hlvx_vu);
bool test_htval_hlv_01a_hlvx_vu(void) {
    TEST_BEGIN("HTVAL-HLV-01a: HLVX.WU @ VU (SPVP=0) gpf reports mtval2 = GPA>>2");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t target = (uintptr_t)test_fault_page;
    /* V=0, HLVX.WU through invalid G-stage PTE, effective priv = VU.
     * Per hypervisor.adoc:1505-1507, HLVX raises the same exceptions
     * as other load instructions -> CAUSE_LOAD_GUEST_PAGE_FAULT (21). */
    bool fired = _fire_hlvx_fault_priv(target, /*flags=*/0, PRIV_U);
    TEST_ASSERT("HLVX load-gpf fired (VU)", fired);
    if (fired) {
        TEST_ASSERT_EQ("mcause = 21 (load-gpf)",
                       trap_get_cause(), CAUSE_LOAD_GUEST_PAGE_FAULT);
        TEST_ASSERT_EQ("mtval2 = GPA>>2",
                       trap_get_htval(), target >> 2);
    }
    hyp_reset_state();
    HYP_TEST_END();
}

TEST_REGISTER(test_htval_hlv_01b_hlvx_vs);
bool test_htval_hlv_01b_hlvx_vs(void) {
    TEST_BEGIN("HTVAL-HLV-01b: HLVX.WU @ VS (SPVP=1) gpf reports mtval2 = GPA>>2");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t target = (uintptr_t)test_fault_page;
    /* V=0, HLVX.WU through invalid G-stage PTE, effective priv = VS.
     * Per hypervisor.adoc:1505-1507, HLVX raises the same exceptions
     * as other load instructions -> CAUSE_LOAD_GUEST_PAGE_FAULT (21). */
    bool fired = _fire_hlvx_fault_priv(target, /*flags=*/0, PRIV_S);
    TEST_ASSERT("HLVX load-gpf fired (VS)", fired);
    if (fired) {
        TEST_ASSERT_EQ("mcause = 21 (load-gpf)",
                       trap_get_cause(), CAUSE_LOAD_GUEST_PAGE_FAULT);
        TEST_ASSERT_EQ("mtval2 = GPA>>2",
                       trap_get_htval(), target >> 2);
    }
    hyp_reset_state();
    HYP_TEST_END();
}

TEST_REGISTER(test_htval_hlv_02_hlv);
bool test_htval_hlv_02_hlv(void) {
    TEST_BEGIN("HTVAL-HLV-02: HLV.D gpf (V=0) reports mtval2 = GPA>>2");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t target = (uintptr_t)test_fault_page;
    /* V=0 -> invalid G-stage PTE -> HLV.D raises CAUSE_LOAD_GUEST_PAGE_FAULT.
     * Trap goes to M-mode; we verify mcause and mtval2. */
    bool fired = _fire_hlv_fault(target, /*flags=*/0);
    TEST_ASSERT("HLV load-gpf fired", fired);
    if (fired) {
        TEST_ASSERT_EQ("mcause = 21 (load-gpf)",
                       trap_get_cause(), CAUSE_LOAD_GUEST_PAGE_FAULT);
        TEST_ASSERT_EQ("mtval2 = GPA>>2",
                       trap_get_htval(), target >> 2);
    }
    hyp_reset_state();
    HYP_TEST_END();
}

TEST_REGISTER(test_htval_hlv_03_hsv);
bool test_htval_hlv_03_hsv(void) {
    TEST_BEGIN("HTVAL-HLV-03: HSV.D gpf (V=0) reports mtval2 = GPA>>2");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t target = (uintptr_t)test_fault_page;
    /* V=0 -> invalid G-stage PTE -> HSV.D raises CAUSE_STORE_GUEST_PAGE_FAULT.
     * Trap goes to M-mode; we verify mcause and mtval2. */
    bool fired = _fire_hsv_fault(target, /*flags=*/0);
    TEST_ASSERT("HSV store-gpf fired", fired);
    if (fired) {
        TEST_ASSERT_EQ("mcause = 23 (store-gpf)",
                       trap_get_cause(), CAUSE_STORE_GUEST_PAGE_FAULT);
        TEST_ASSERT_EQ("mtval2 = GPA>>2",
                       trap_get_htval(), target >> 2);
    }
    hyp_reset_state();
    HYP_TEST_END();
}

TEST_REGISTER(test_htval_hlv_04_hlvx_bare);
bool test_htval_hlv_04_hlvx_bare(void) {
    TEST_BEGIN("HTVAL-HLV-04: HLVX.WU (vsatp=BARE) gpf reports mtval2 = GPA>>2");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t target = (uintptr_t)test_fault_page;
    /* V=0, HLVX.WU with vsatp=BARE: VA is directly used as GPA.
     * No VS-stage translation involved. G-stage PTE is invalid (V=0).
     * Per hypervisor.adoc:1505-1507, HLVX raises load-class exceptions
     * -> CAUSE_LOAD_GUEST_PAGE_FAULT (21), NOT inst GPF (20). */
    bool fired = _fire_hlvx_fault_bare(target, /*flags=*/0);
    TEST_ASSERT("HLVX load-gpf fired (BARE)", fired);
    if (fired) {
        TEST_ASSERT_EQ("mcause = 21 (load-gpf)",
                       trap_get_cause(), CAUSE_LOAD_GUEST_PAGE_FAULT);
        TEST_ASSERT_EQ("mtval2 = GPA>>2",
                       trap_get_htval(), target >> 2);
    }
    hyp_reset_state();
    HYP_TEST_END();
}
