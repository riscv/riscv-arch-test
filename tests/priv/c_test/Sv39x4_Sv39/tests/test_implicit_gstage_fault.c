/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * common/hyp/tests_2stage/test_group06_implicit_gstage_fault.c
 *
 * Group 6 - Implicit G-stage fault during VS-stage page-table walk
 *           (TS-IMPL-01, 03, 04, 06)
 *
 * NOTE: TS-IMPL-02 removed (framework cannot isolate mid-level PT).
 *       TS-IMPL-05 removed (spec does not mandate GVA/stval on this path).
 *
 * When V=1 the hypervisor extension subjects every VS-stage page-table
 * read to G-stage translation. If the GPA holding a VS-stage PT page
 * is unmapped (or has insufficient G-stage permissions), the implicit
 * access raises a guest-page-fault whose:
 *   - stval  = original GVA (set by hstatus.GVA = 1)
 *   - htval  = faulting PTE GPA >> 2 (NOT the PT page base) or zero
 *   - htinst = pseudoinstruction (0x00003000 read / 0x00003020 write),
 *              mandated when htval != 0 (norm:H_trap_xtinst_guestpage)
 *   - cause  = 20 / 21 / 23 (fetch / load / store guest-page-fault)
 *
 * All cases here build the canonical 2-stage identity layout via
 * ts2_setup_full(), then surgically corrupt one page of the VS-level
 * page-table chain in G-stage to induce the fault.
 *
 * Design note: ts2_invalidate_vs_pt_in_g(ctx, va, level) is the
 * framework helper that returns the GPA of the VS-stage PT page at
 * @level for @va and writes a V=0 G-stage leaf at that GPA. We use
 * the returned PT GPA to validate htval bits in the trap record.
 * =================================================================== */

#ifndef SUITE_HGATP_MODE
#error "SUITE_HGATP_MODE must be defined before including this file"
#endif
#ifndef SUITE_VSATP_MODE
#error "SUITE_VSATP_MODE must be defined before including this file"
#endif


/* RV64 H-extension pseudoinstructions reported in htinst when a fault
 * stems from an *implicit* memory access during page-table walk:
 *   - 0x00003000 = "any read"
 *   - 0x00003020 = "any write" (used for hardware A/D-bit update store)
 * The values depend on VSXLEN (SPEC <<pseudoinsts>>: the RV32 values
 * 0x00002000 / 0x00002020 apply when VSXLEN=32). This repository is
 * RV64 only, so the RV64 values are used unconditionally.
 */
#define G6_HTINST_READ_RV64    0x00003000UL
#define G6_HTINST_WRITE_RV64   0x00003020UL

/* ---- file-scope helpers ---------------------------------------------- */

/* Compute the exact GPA of the PTE that maps @va at @level within the
 * page table page whose base is @pt_page_base.
 * Per spec, htval reports this value >> 2 on implicit-PT-walk faults.
 * Formula: pt_page_base + VPN[level](va) * PTE_SIZE(8). */
#define PTE_GPA_IN_PT(pt_page_base, va, level) \
    ((pt_page_base) + (((uintptr_t)(va) >> (12 + (level)*9)) & 0x1FFUL) * 8)

/* Return the VS-stage root level index for the active vs_mode in @ctx.
 * SV39 -> 2, SV48 -> 3, SV57 -> 4 (matches ctx->vs_ctx.levels - 1). */
static int g6_vs_root_level(two_stage_ctx_t *ctx) {
    return ctx->vs_ctx.levels - 1;
}

/* ===================================================================
 * TS-IMPL-01: VS-stage leaf PT page in G-stage unmapped
 *             VS-mode load -> load-guest-page-fault
 *
 * We invalidate the *leaf* (PT_LEVEL_4K) PT page rather than the root
 * because the root is shared with the kernel-image fetch path: making
 * the root invalid would fault VS-mode fetch before the load can run.
 * The leaf PT page covers only the 2MB band containing test_data_area,
 * which lies inside .vm_test_region (separate from .text).
 * =================================================================== */
TEST_REGISTER(test_ts_impl_01_root_unmapped_load);
bool test_ts_impl_01_root_unmapped_load(void) {
    TEST_BEGIN("TS-IMPL-01: VS-leaf PT unmapped in G; load -> cause=21");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    uintptr_t va = (uintptr_t)test_data_area;

    /* Mark the VS-stage *leaf* PT page as INVALID in G-stage.
     * Returns the PT page GPA so we can validate htval. */
    uintptr_t pt_gpa = ts2_invalidate_vs_pt_in_g(&ctx, va, PT_LEVEL_4K);
    TEST_ASSERT("VS leaf PT GPA resolvable", pt_gpa != 0);

    bool ok = ts2_run_check_fault(&ctx, test_vs_load_expect_fault, va,
                                  CAUSE_LOAD_GUEST_PAGE_FAULT);
    TEST_ASSERT("cause = load-guest-page-fault (21)", ok);
    CHECK_IMPLICIT_FAULT_REPORT(PTE_GPA_IN_PT(pt_gpa, va, 0) >> 2,
                                G6_HTINST_READ_RV64);

    HYP_TEST_END();
}

/* TS-IMPL-02: removed — framework cannot isolate mid-level PT page
 * from the kernel-image fetch path in the current single-image layout. */

/* ===================================================================
 * TS-IMPL-03: VS-stage PT page read-only in G-stage; store whose VS
 *             leaf PTE needs a D-bit update (W=1, A=1, D=0).
 *
 * With hardware A/D update enabled (Svadu: henvcfg.ADUE gates the
 * VS-stage update, menvcfg.ADUE gates G-stage), the machine performs
 * an implicit STORE to the VS-level PTE to set D. That implicit store
 * goes through G-stage translation and hits the read-only PT page,
 * raising a guest-page-fault whose report is governed by:
 *   - norm:H_vm_gpapriv: the exception is reported for the original
 *     access type -> cause = 23 (store guest-page-fault);
 *   - norm:htval_trapval: htval = PTE GPA >> 2 or zero;
 *   - norm:H_trap_xtinst_guestpage + norm:H_trap_xtinst_guestpage_rw:
 *     the implicit store is a VS-level A/D update, so when htval is
 *     nonzero htinst MUST be the WRITE pseudoinstruction
 *     0x00003020 (RV64); zero is NOT allowed.
 *
 * Without Svadu (ADUE read-only zero), the D=0 store raises a
 * VS-stage store page-fault on the original access (Svade): cause 15,
 * and the write pseudoinstruction case never arises.
 * =================================================================== */
TEST_REGISTER(test_ts_impl_03_pt_readonly_store);
bool test_ts_impl_03_pt_readonly_store(void) {
    TEST_BEGIN("TS-IMPL-03: VS-PT G-readonly + D=0 store (write pseudoinst)");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    gpt_pool_reset();
    pt_pool_reset();
    two_stage_init(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    uintptr_t va = (uintptr_t)test_data_area;
    /* Bring up the canonical full layout, then patch VS leaf flags:
     * W=1 so the store passes VS-stage permission checks, A=1 and
     * D=0 so the store requires a D-bit update. (W must be 1: the
     * permission check precedes the A/D step in the translation
     * algorithm, so with W=0 a hardware D-update can never occur.) */
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);
    {
        uintptr_t *pte = pt_get_pte(&ctx.vs_ctx, va, PT_LEVEL_4K);
        TEST_ASSERT("VS leaf PTE resolvable", pte != NULL);
        if (pte) {
            uintptr_t ppn_bits = (*pte) & ~((1UL << 10) - 1UL);
            *pte = ppn_bits | PTE_V | PTE_R | PTE_W | PTE_X | PTE_A; /* no D */
        }
    }

    /* Make the VS-stage *leaf* PT page read-only in G-stage: the
     * implicit D-bit-update store must fault there. */
    uintptr_t pt_gpa = two_stage_vs_pt_page_addr(&ctx, va, PT_LEVEL_4K);
    TEST_ASSERT("VS leaf PT GPA resolvable", pt_gpa != 0);
    ts2_g_override_4k(&ctx, pt_gpa, PTE_V | PTE_R | PTE_U | PTE_A); /* no W */

    /* Enable hardware A/D update (Svadu) and probe whether the
     * platform actually implements it: the ADUE bits stick only when
     * Svadu is present (norm:menvcfg_adue_op / henvcfg_adue_op). */
    ts2_enable_adue();
    bool adue_on = ((tsbi_csr_read(CSR_MENVCFG) & MENVCFG_ADUE) != 0) &&
                   ((henvcfg_read() & HENVCFG_ADUE) != 0);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_store_expect_fault, va);
    bool fired = trap_was_triggered();
    uintptr_t cause = fired ? trap_get_cause() : 0;
    trap_expect_end();

    two_stage_cleanup(&ctx);
    ts2_disable_adue();

    TEST_ASSERT("a fault must fire", fired);
    /* Known non-compliance: QEMU (as of 8.x/9.x) performs the Svadu
     * D-bit update without subjecting the implicit store to G-stage
     * protection (violates norm:H_vm_gstagetrans + H_vm_gpapriv): it
     * silently sets D and completes the store, so no trap fires.
     * This test intentionally stays FAIL on such implementations and
     * must not be relaxed (project rule: never adapt tests to a
     * non-spec-compliant simulator). */
    if (fired) {
        if (adue_on) {
            /* Hardware A/D path: the implicit store that sets D faults
             * in G-stage, reported as store guest-page-fault per the
             * original access type (norm:H_vm_gpapriv). */
            TEST_ASSERT_EQ("cause = store guest-page-fault (23)",
                           cause, (uintptr_t)CAUSE_STORE_GUEST_PAGE_FAULT);
            CHECK_IMPLICIT_FAULT_REPORT(PTE_GPA_IN_PT(pt_gpa, va, 0) >> 2,
                                        G6_HTINST_WRITE_RV64);
        } else {
            /* No Svadu: Svade raises a VS-stage store page-fault on
             * the original access; the write case never arises
             * (norm:H_trap_xtinst_guestpage_rw). */
            TEST_ASSERT_EQ("cause = store page-fault (15, Svade)",
                           cause, (uintptr_t)CAUSE_STORE_PAGE_FAULT);
        }
    }

    HYP_TEST_END();
}

/* ===================================================================
 * TS-IMPL-04: VS-stage PT page mapped U=0 in G-stage. Since G-stage
 *             treats every guest access as U-mode, U=0 forces an
 *             implicit-access fault.
 * =================================================================== */
TEST_REGISTER(test_ts_impl_04_pt_no_u);
bool test_ts_impl_04_pt_no_u(void) {
    TEST_BEGIN("TS-IMPL-04: VS-PT G-stage U=0 -> implicit fault");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    uintptr_t va = (uintptr_t)test_data_area;
    uintptr_t pt_gpa = two_stage_vs_pt_page_addr(&ctx, va, PT_LEVEL_4K);
    TEST_ASSERT("VS leaf PT GPA resolvable", pt_gpa != 0);

    /* Override the leaf PT GPA in G-stage with R+A but NO U bit. */
    ts2_g_override_4k(&ctx, pt_gpa, PTE_V | PTE_R | PTE_A);

    bool ok = ts2_run_check_fault(&ctx, test_vs_load_expect_fault, va,
                                  CAUSE_LOAD_GUEST_PAGE_FAULT);
    TEST_ASSERT("cause = load-guest-page-fault (21)", ok);
    CHECK_IMPLICIT_FAULT_REPORT(PTE_GPA_IN_PT(pt_gpa, va, 0) >> 2,
                                G6_HTINST_READ_RV64);

    HYP_TEST_END();
}

/* TS-IMPL-05: removed — spec does not mandate hstatus.GVA/stval reporting
 * on implicit-PT-walk faults; behavior is implementation-defined. */

/* ===================================================================
 * TS-IMPL-06: VS-mode FETCH whose PT walk implicit-faults.
 *             Cause = 20 (fetch-guest-page-fault).
 * =================================================================== */
TEST_REGISTER(test_ts_impl_06_fetch);
bool test_ts_impl_06_fetch(void) {
    TEST_BEGIN("TS-IMPL-06: VS-fetch with VS-PT G-unmapped -> cause=20");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    int root_level = g6_vs_root_level(&ctx);
    uintptr_t va = (uintptr_t)test_exec_page;
    uintptr_t pt_gpa = ts2_invalidate_vs_pt_in_g(&ctx, va, PT_LEVEL_4K);
    TEST_ASSERT("VS leaf PT GPA resolvable", pt_gpa != 0);
    (void)root_level;

    bool ok = ts2_run_check_fault(&ctx, test_vs_exec_expect_fault, va,
                                  CAUSE_INST_GUEST_PAGE_FAULT);
    TEST_ASSERT("cause = fetch-guest-page-fault (20)", ok);
    CHECK_IMPLICIT_FAULT_REPORT(PTE_GPA_IN_PT(pt_gpa, va, 0) >> 2,
                                G6_HTINST_READ_RV64);

    HYP_TEST_END();
}
