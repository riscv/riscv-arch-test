/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 6: hgatp mode coverage (HTVAL-MOD-*)
 *
 * Spec anchor:
 *   norm:H_htval — htval semantics are mode-independent (Sv39x4 /
 *   Sv48x4 / Sv57x4 all share GPA>>2 mapping).
 *
 * Each test fires the same load-on-R=0 fault under a different
 * hgatp mode and checks htval = GPA >> 2.
 *
 *   HTVAL-MOD-01  Sv39x4
 *   HTVAL-MOD-02  Sv48x4
 *   HTVAL-MOD-03  Sv57x4
 *   HTVAL-MOD-04  Sv39x4 with high-order GPA (still expected to be
 *                 reported correctly; test_fault_page lives in low
 *                 GPA, so this is a sanity replay rather than a
 *                 new high-bit case — high-bit overflow is sv39x4
 *                 territory and tested in sv39x4/test_gpa_high.c)
 * =================================================================== */

static bool _run_mode_check(int g_mode, const char *mode_name) {
    if (!hgatp_supports_mode(g_mode)) {
        LOG_W("%s not supported\n", mode_name);
        return true;
    }
    uintptr_t target = (uintptr_t)test_fault_page;
    uintptr_t flags  = (G_FLAGS_RWXU_AD & ~PTE_R);

    bool fired = _fire_load_fault_mode(target, flags, g_mode);
    bool ok = fired;
    if (fired) {
        if (trap_get_cause() != CAUSE_LOAD_GUEST_PAGE_FAULT) {
            LOG_E("[%s] cause %lu != 21\n",
                  mode_name, (unsigned long)trap_get_cause());
            ok = false;
        }
        if (trap_get_htval() != target >> 2) {
            LOG_E("[%s] htval 0x%lx != 0x%lx\n",
                  mode_name,
                  (unsigned long)trap_get_htval(),
                  (unsigned long)(target >> 2));
            ok = false;
        }
    } else {
        LOG_E("[%s] no trap fired\n", mode_name);
    }
    hyp_reset_state();
    return ok;
}

TEST_REGISTER(test_htval_mod_01_sv39x4);
bool test_htval_mod_01_sv39x4(void) {
    TEST_BEGIN("HTVAL-MOD-01: htval = GPA>>2 under hgatp.MODE = Sv39x4");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(HGATP_MODE_SV39X4);
    TEST_ASSERT("Sv39x4 htval ok", _run_mode_check(HGATP_MODE_SV39X4, "Sv39x4"));
    HYP_TEST_END();
}

TEST_REGISTER(test_htval_mod_02_sv48x4);
bool test_htval_mod_02_sv48x4(void) {
    TEST_BEGIN("HTVAL-MOD-02: htval = GPA>>2 under hgatp.MODE = Sv48x4");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(HGATP_MODE_SV48X4);
    TEST_ASSERT("Sv48x4 htval ok", _run_mode_check(HGATP_MODE_SV48X4, "Sv48x4"));
    HYP_TEST_END();
}

TEST_REGISTER(test_htval_mod_03_sv57x4);
bool test_htval_mod_03_sv57x4(void) {
    TEST_BEGIN("HTVAL-MOD-03: htval = GPA>>2 under hgatp.MODE = Sv57x4");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(HGATP_MODE_SV57X4);
    TEST_ASSERT("Sv57x4 htval ok", _run_mode_check(HGATP_MODE_SV57X4, "Sv57x4"));
    HYP_TEST_END();
}

TEST_REGISTER(test_htval_mod_04_sv39x4_replay);
bool test_htval_mod_04_sv39x4_replay(void) {
    TEST_BEGIN("HTVAL-MOD-04: Sv39x4 sanity replay (deterministic htval)");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(HGATP_MODE_SV39X4);
    bool a = _run_mode_check(HGATP_MODE_SV39X4, "Sv39x4#1");
    bool b = _run_mode_check(HGATP_MODE_SV39X4, "Sv39x4#2");
    TEST_ASSERT("replay matches", a && b);
    HYP_TEST_END();
}

/* ===================================================================
 * GPA overflow tests (HTVAL-MOD-05/06/07)
 *
 * When a GPA exceeds the address range supported by the G-stage mode
 * (bits 63:41 for Sv39x4, 63:50 for Sv48x4, 63:59 for Sv57x4), the
 * hardware must generate a GPF and htval must record the full
 * overflow GPA >> 2.
 *
 * Strategy: set up G-stage with kernel mapped at low addresses. Use
 * vsatp=BARE so GVA=GPA. VS-mode accesses an overflow address, which
 * the hardware should reject before even walking the page table.
 * =================================================================== */

static bool _fire_overflow_load_fault(int g_mode, uintptr_t overflow_gpa) {
    two_stage_ctx_t ctx;
    gpt_pool_reset();
    two_stage_init(&ctx, SATP_MODE_BARE, g_mode);

    /* Identity-map kernel at 2MB (so VS-mode code can execute). */
    uintptr_t lo_base = PLATFORM_MEM_BASE & ~(PAGE_SIZE_2M - 1);
    uintptr_t lo_end  = (uintptr_t)__vm_test_region_start
                        & ~(PAGE_SIZE_2M - 1);
    two_stage_setup_identity(&ctx, lo_base, lo_end - lo_base,
                             G_FLAGS_RWXU_AD, PT_LEVEL_2M);

    /* Map test region at 4KB (for VS code/stack). */
    uintptr_t r_start = (uintptr_t)__vm_test_region_start;
    uintptr_t r_size  = (uintptr_t)__vm_test_region_end - r_start;
    two_stage_setup_identity(&ctx, r_start, r_size,
                             G_FLAGS_RWXU_AD, PT_LEVEL_4K);

    /* Do NOT map overflow_gpa — it's out of range; GPF fires
     * due to high-bit violation, not page table miss. */

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_load_expect_fault, overflow_gpa);
    bool fired = trap_was_triggered();
    trap_expect_end();

    two_stage_cleanup(&ctx);
    return fired;
}

TEST_REGISTER(test_htval_mod_05_sv39x4_overflow);
bool test_htval_mod_05_sv39x4_overflow(void) {
    TEST_BEGIN("HTVAL-MOD-05: Sv39x4 GPA bit41=1 overflow -> GPF with htval");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(HGATP_MODE_SV39X4);

    /* Sv39x4 requires GPA bits 63:41 == 0. Bit 41 set = overflow. */
    uintptr_t overflow_gpa = 1UL << 41;

    bool fired = _fire_overflow_load_fault(HGATP_MODE_SV39X4, overflow_gpa);
    TEST_ASSERT("overflow GPF fired", fired);
    if (fired) {
        TEST_ASSERT_EQ("cause = 21 (load-gpf)",
                       trap_get_cause(), CAUSE_LOAD_GUEST_PAGE_FAULT);
        TEST_ASSERT_EQ("htval = overflow_GPA>>2",
                       trap_get_htval(), overflow_gpa >> 2);
    }
    hyp_reset_state();
    HYP_TEST_END();
}

TEST_REGISTER(test_htval_mod_06_sv48x4_overflow);
bool test_htval_mod_06_sv48x4_overflow(void) {
    TEST_BEGIN("HTVAL-MOD-06: Sv48x4 GPA bit50=1 overflow -> GPF with htval");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(HGATP_MODE_SV48X4);

    /* Sv48x4 requires GPA bits 63:50 == 0. Bit 50 set = overflow. */
    uintptr_t overflow_gpa = 1UL << 50;

    bool fired = _fire_overflow_load_fault(HGATP_MODE_SV48X4, overflow_gpa);
    TEST_ASSERT("overflow GPF fired", fired);
    if (fired) {
        TEST_ASSERT_EQ("cause = 21 (load-gpf)",
                       trap_get_cause(), CAUSE_LOAD_GUEST_PAGE_FAULT);
        TEST_ASSERT_EQ("htval = overflow_GPA>>2",
                       trap_get_htval(), overflow_gpa >> 2);
    }
    hyp_reset_state();
    HYP_TEST_END();
}

TEST_REGISTER(test_htval_mod_07_sv57x4_overflow);
bool test_htval_mod_07_sv57x4_overflow(void) {
    TEST_BEGIN("HTVAL-MOD-07: Sv57x4 GPA bit59=1 overflow -> GPF with htval");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(HGATP_MODE_SV57X4);

    /* Sv57x4 requires GPA bits 63:59 == 0. Bit 59 set = overflow. */
    uintptr_t overflow_gpa = 1UL << 59;

    bool fired = _fire_overflow_load_fault(HGATP_MODE_SV57X4, overflow_gpa);
    TEST_ASSERT("overflow GPF fired", fired);
    if (fired) {
        TEST_ASSERT_EQ("cause = 21 (load-gpf)",
                       trap_get_cause(), CAUSE_LOAD_GUEST_PAGE_FAULT);
        TEST_ASSERT_EQ("htval = overflow_GPA>>2",
                       trap_get_htval(), overflow_gpa >> 2);
    }
    hyp_reset_state();
    HYP_TEST_END();
}
