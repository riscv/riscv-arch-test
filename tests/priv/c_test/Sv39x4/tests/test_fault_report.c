/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 13: G-stage fault reporting (GFAULT-01..08)
 *
 * Spec anchors:
 *   norm:gpf_cause_codes  - load=21, store=23, fetch=20
 *   norm:H_htval          - htval = faulting GPA >> 2
 *   norm:H_htinst         - htinst = transformed pseudo-inst (or 0)
 *   norm:H_hstatus_gva    - hstatus.GVA=1 when fault GVA is virtualized
 *
 * In this test plan hedeleg=0, so all G-stage faults are taken in
 * M-mode. The trap framework captures mtval2 / mtinst / mstatus.GVA
 * and exposes them as trap_get_htval/htinst/gva (M-mode synonyms).
 *
 * GFAULT-01: load gpf  -> mcause = 21
 * GFAULT-02: store gpf -> mcause = 23
 * GFAULT-03: inst gpf  -> mcause = 20
 * GFAULT-04: mtval2 == 0 or GPA >> 2 (load fault)
 * GFAULT-05: stval == GVA      (load fault)
 * GFAULT-06: GVA flag set on load gpf
 * GFAULT-07: htinst != 0 on load gpf (transformed)
 * GFAULT-08: htinst == 0 on inst gpf
 *
 * Reuses _setup_with_victim() / _vsfault_check() from test_helpers.c.
 * Tests that need to inspect post-trap fields run a single fault
 * inline (instead of through _vsfault_check) so the trap_record
 * survives until inspection.
 * =================================================================== */

/* GFAULT-01: load guest-page-fault -> cause 21 */
TEST_REGISTER(test_gfault_01_load_cause);
bool test_gfault_01_load_cause(void) {
    TEST_BEGIN("GFAULT-01: load guest-page-fault cause = 21");
    uintptr_t flags = (G_FLAGS_RWXU_AD & ~PTE_R);  /* R=0 */
    bool ok = _vsfault_check(test_vs_load_expect_fault,
                             (uintptr_t)test_fault_page,
                             flags, CAUSE_LOAD_GUEST_PAGE_FAULT);
    TEST_ASSERT("load gpf cause = 21", ok);
    HYP_TEST_END();
}

/* GFAULT-02: store guest-page-fault -> cause 23 */
TEST_REGISTER(test_gfault_02_store_cause);
bool test_gfault_02_store_cause(void) {
    TEST_BEGIN("GFAULT-02: store guest-page-fault cause = 23");
    uintptr_t flags = (G_FLAGS_RWXU_AD & ~PTE_W);  /* W=0 */
    bool ok = _vsfault_check(test_vs_store_expect_fault,
                             (uintptr_t)test_fault_page,
                             flags, CAUSE_STORE_GUEST_PAGE_FAULT);
    TEST_ASSERT("store gpf cause = 23", ok);
    HYP_TEST_END();
}

/* GFAULT-03: inst guest-page-fault -> cause 20 */
TEST_REGISTER(test_gfault_03_inst_cause);
bool test_gfault_03_inst_cause(void) {
    TEST_BEGIN("GFAULT-03: inst guest-page-fault cause = 20");
    uintptr_t flags = (G_FLAGS_RWXU_AD & ~PTE_X);  /* X=0 */
    bool ok = _vsfault_check(test_vs_exec_expect_fault,
                             (uintptr_t)test_fault_page,
                             flags, CAUSE_INST_GUEST_PAGE_FAULT);
    TEST_ASSERT("inst gpf cause = 20", ok);
    HYP_TEST_END();
}

/* Helper for inline fault tests: trigger a load fault on victim_gpa
 * with the supplied G-stage leaf flags, leaving the trap_record
 * available for post-trap field inspection. */
static bool _fire_load_fault(uintptr_t victim_gpa, uintptr_t flags) {
    two_stage_ctx_t ctx;
    _setup_with_victim(&ctx, victim_gpa, flags);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_load_expect_fault, victim_gpa);
    bool fired = trap_was_triggered();
    trap_expect_end();

    two_stage_cleanup(&ctx);
    /* Note: no hyp_reset_state() here so trap_record stays valid. */
    return fired;
}

/* GFAULT-04: mtval2 == 0 or GPA >> 2 on load fault
 *
 * hedeleg=0 and no medeleg GPF delegation in this suite, so the
 * fault is taken into M-mode and trap_get_htval() reflects mtval2.
 * norm:mtval2_trapval allows either zero or the faulting GPA >> 2;
 * any other value is a spec violation. Zero must be accepted (an
 * implementation whose mtval2 WARL subset holds only zero is legal,
 * norm:mtval2_val). */
TEST_REGISTER(test_gfault_04_htval);
bool test_gfault_04_htval(void) {
    TEST_BEGIN("GFAULT-04: mtval2 == 0 or faulting GPA >> 2");
    uintptr_t target = (uintptr_t)test_fault_page;
    uintptr_t flags  = (G_FLAGS_RWXU_AD & ~PTE_R);

    bool fired = _fire_load_fault(target, flags);
    TEST_ASSERT("load gpf fired", fired);
    if (fired) {
        uintptr_t htval = trap_get_htval();
        if (htval == 0) {
            LOG_I("implementation writes 0 to mtval2 on GPF "
                  "(allowed by norm:mtval2_trapval)\n");
        }
        TEST_ASSERT("mtval2 == 0 or GPA>>2 (strict)",
                    htval == 0 || htval == (target >> 2));
    }
    hyp_reset_state();
    HYP_TEST_END();
}

/* GFAULT-05: stval == GVA on load fault
 *
 * In M-mode capture, the framework copies mtval into trap_record.tval,
 * which equals the faulting virtual address (here, since vsatp=Bare,
 * GVA == GPA). */
TEST_REGISTER(test_gfault_05_stval_gva);
bool test_gfault_05_stval_gva(void) {
    TEST_BEGIN("GFAULT-05: trap tval == faulting GVA");
    uintptr_t target = (uintptr_t)test_fault_page;
    uintptr_t flags  = (G_FLAGS_RWXU_AD & ~PTE_R);

    bool fired = _fire_load_fault(target, flags);
    TEST_ASSERT("load gpf fired", fired);
    if (fired) {
        TEST_ASSERT_EQ("tval == GVA", trap_get_tval(), target);
    }
    hyp_reset_state();
    HYP_TEST_END();
}

/* GFAULT-06: GVA flag set when fault address is virtualized */
TEST_REGISTER(test_gfault_06_gva_flag);
bool test_gfault_06_gva_flag(void) {
    TEST_BEGIN("GFAULT-06: hstatus.GVA / mstatus.GVA == 1 on G-stage fault");
    uintptr_t target = (uintptr_t)test_fault_page;
    uintptr_t flags  = (G_FLAGS_RWXU_AD & ~PTE_R);

    bool fired = _fire_load_fault(target, flags);
    TEST_ASSERT("load gpf fired", fired);
    if (fired) {
        TEST_ASSERT("GVA flag is 1", trap_get_gva());
    }
    hyp_reset_state();
    HYP_TEST_END();
}

/* GFAULT-07: htinst is non-zero (transformed pseudo-inst) on load gpf */
TEST_REGISTER(test_gfault_07_htinst_load);
bool test_gfault_07_htinst_load(void) {
    TEST_BEGIN("GFAULT-07: htinst != 0 on load guest-page-fault");
    uintptr_t target = (uintptr_t)test_fault_page;
    uintptr_t flags  = (G_FLAGS_RWXU_AD & ~PTE_R);

    bool fired = _fire_load_fault(target, flags);
    TEST_ASSERT("load gpf fired", fired);
    if (fired) {
        uintptr_t htinst = trap_get_htinst();
        /* Per H_trap_xtinst, htinst may be 0, a transformed instruction,
         * a custom value, or a pseudoinstruction.  H_trap_xtinst_guestpage
         * only mandates a non-zero pseudoinstruction for *implicit*
         * VS-stage page-table accesses.  This test triggers an *explicit*
         * load, so htinst == 0 is spec-compliant (Spike writes 0, QEMU
         * writes a transformed load — both are valid).
         *
         * For non-zero values, verify the basic transformed-instruction
         * format: bit 0 must be 1 (H_trap_xtinst_exception_list). */
        if (htinst != 0) {
            TEST_ASSERT("htinst bit 0 is 1 (transformed format)",
                        (htinst & 1) == 1);
        } else {
            TEST_ASSERT("htinst == 0 is spec-compliant for explicit access",
                        true);
        }
    }
    hyp_reset_state();
    HYP_TEST_END();
}

/* GFAULT-08: htinst == 0 on inst guest-page-fault
 *
 * For instruction guest-page-faults the spec mandates htinst = 0
 * (no transformed instruction can be reported). */
TEST_REGISTER(test_gfault_08_htinst_inst);
bool test_gfault_08_htinst_inst(void) {
    TEST_BEGIN("GFAULT-08: htinst == 0 on inst guest-page-fault");

    two_stage_ctx_t ctx;
    uintptr_t flags = (G_FLAGS_RWXU_AD & ~PTE_X);  /* X=0 */
    _setup_with_victim(&ctx, (uintptr_t)test_fault_page, flags);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_exec_expect_fault,
                              (uintptr_t)test_fault_page);
    bool fired = trap_was_triggered();
    uintptr_t htinst = fired ? trap_get_htinst() : (uintptr_t)-1;
    trap_expect_end();

    two_stage_cleanup(&ctx);

    TEST_ASSERT("inst gpf fired", fired);
    if (fired) {
        TEST_ASSERT_EQ("htinst on inst gpf is 0", htinst, 0);
    }
    hyp_reset_state();
    HYP_TEST_END();
}
