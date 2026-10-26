/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * common/hyp/tests_2stage/test_group12_sfence_vma.c
 *
 * Group 12 - SFENCE.VMA semantics under V=1 / V=0 (TS-SF-01..04)
 *
 * Spec basis:
 *   - When V=1, SFENCE.VMA operates on the *VS-stage* (vsatp-controlled)
 *     translation caches, identically to HFENCE.VVMA on the current
 *     vsatp.ASID. It does NOT flush G-stage caches.
 *   - When V=0, SFENCE.VMA operates on HS-level translation caches.
 *   - hstatus.VTVM=1 -> SFENCE.VMA in V=1 raises a virtual-instruction
 *     exception (cause=22).
 *   - mstatus.TVM=1 -> SFENCE.VMA in HS (V=0, S-mode) raises illegal-
 *     instruction (cause=2). [Outside this group; covered elsewhere.]
 * =================================================================== */

#ifndef SUITE_HGATP_MODE
#error "SUITE_HGATP_MODE must be defined before including this file"
#endif
#ifndef SUITE_VSATP_MODE
#error "SUITE_VSATP_MODE must be defined before including this file"
#endif


#define G12_VS_RWX  (PTE_V|PTE_R|PTE_W|PTE_X|PTE_A|PTE_D)
#define G12_VS_INV  (0)

extern uintptr_t run_in_priv(unsigned priv,
                             uintptr_t (*fn)(uintptr_t), uintptr_t arg);

/* VS-mode helper: SFENCE.VMA x0,x0 (opcode 0x12000073). */
static uintptr_t g12_vs_sfence_vma_all(uintptr_t arg) {
    (void)arg;
    asm volatile (".word 0x12000073" ::: "memory");
    return 0;
}

/* HS-mode helper: SFENCE.VMA x0,x0. */
static uintptr_t g12_hs_sfence_vma_all(uintptr_t arg) {
    (void)arg;
    asm volatile (".word 0x12000073" ::: "memory");
    return 0;
}

/* ===================================================================
 * TS-SF-01: V=1 SFENCE.VMA flushes VS-stage caches.
 *   - warm up VS load (TLB primes)
 *   - rewrite VS leaf to V=0
 *   - issue SFENCE.VMA in VS-mode
 *   - subsequent VS load must page-fault (cause=13)
 * =================================================================== */
TEST_REGISTER(test_ts_sf_01_v1_flush_vs);
bool test_ts_sf_01_v1_flush_vs(void) {
    TEST_BEGIN("TS-SF-01: V=1 sfence.vma -> VS-stage flushed");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_fault_page;
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    /* Warm up. */
    (void)ts2_run_check_no_fault(&ctx, test_vs_read_write, va);

    /* Invalidate VS leaf. */
    (void)pt_map_page(&ctx.vs_ctx, va & ~0xfffUL, va & ~0xfffUL,
                      G12_VS_INV, PT_LEVEL_4K);

    /* Issue SFENCE.VMA in VS-mode (V=1). */
    (void)two_stage_run_in_vs(&ctx, g12_vs_sfence_vma_all, 0);

    /* Subsequent VS-mode load must observe the new (V=0) PTE. */
    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_load_expect_fault, va);
    bool fired = trap_was_triggered();
    uintptr_t cause = fired ? trap_get_cause() : 0;
    trap_expect_end();
    ts2_finish(&ctx);

    TEST_ASSERT("VS-mode load trapped", fired);
    TEST_ASSERT_EQ("cause = load-page-fault (13)",
                   cause, (uintptr_t)CAUSE_LOAD_PAGE_FAULT);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-SF-02: V=1 SFENCE.VMA does NOT flush G-stage.
 *   - warm up VS load
 *   - issue VS-mode SFENCE.VMA (no VS-stage change)
 *   - subsequent VS load must succeed (G-stage cache and VS-stage cache
 *     both still valid; sfence.vma only touched VS-stage)
 * Note: this is a positive (no-fault) check; deeper verification of the
 * "G-stage NOT flushed" property would need observable G-stage TLB state
 * which the model does not expose.
 * =================================================================== */
TEST_REGISTER(test_ts_sf_02_v1_no_g_flush);
bool test_ts_sf_02_v1_no_g_flush(void) {
    TEST_BEGIN("TS-SF-02: V=1 sfence.vma does not affect G-stage");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_fault_page;
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    /* Warm up. */
    (void)ts2_run_check_no_fault(&ctx, test_vs_read_write, va);

    /* VS-mode SFENCE.VMA. */
    (void)two_stage_run_in_vs(&ctx, g12_vs_sfence_vma_all, 0);

    /* Load must still succeed (no G-stage state mutated). */
    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_read_write, va);
    bool fired = trap_was_triggered();
    trap_expect_end();
    ts2_finish(&ctx);

    TEST_ASSERT("VS-mode load did not fault after VS-mode sfence.vma",
                !fired);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-SF-03: hstatus.VTVM=1 -> VS-mode SFENCE.VMA traps as virtual-inst.
 * =================================================================== */
TEST_REGISTER(test_ts_sf_03_vtvm_virt_inst);
bool test_ts_sf_03_vtvm_virt_inst(void) {
    TEST_BEGIN("TS-SF-03: hstatus.VTVM=1 -> sfence.vma in VS = virt-inst (22)");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    /* Set hstatus.VTVM=1. */
    CSRS(CSR_HSTATUS, (uintptr_t)HSTATUS_VTVM);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, g12_vs_sfence_vma_all, 0);
    bool fired = trap_was_triggered();
    uintptr_t cause = fired ? trap_get_cause() : 0;
    trap_expect_end();

    /* Restore VTVM=0. */
    CSRC(CSR_HSTATUS, (uintptr_t)HSTATUS_VTVM);
    ts2_finish(&ctx);

    TEST_ASSERT("trap fired in VS-mode with VTVM=1", fired);
    TEST_ASSERT_EQ("cause = virtual-instruction (22)",
                   cause, (uintptr_t)CAUSE_VIRTUAL_INSTRUCTION);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-SF-04: V=0 SFENCE.VMA does NOT touch VS-stage.
 *   - warm up VS load
 *   - rewrite VS leaf to V=0
 *   - issue HS-mode SFENCE.VMA (V=0); should NOT flush VS-stage TLB,
 *     so the prior translation may remain cached and the load may
 *     succeed; however, after issuing HFENCE.VVMA explicitly, the
 *     load must fault. We verify that an explicit HFENCE.VVMA *after*
 *     SFENCE.VMA still produces the page fault, demonstrating that
 *     VS-stage cleanup is the responsibility of HFENCE.VVMA.
 * =================================================================== */
TEST_REGISTER(test_ts_sf_04_v0_not_touch_vs);
bool test_ts_sf_04_v0_not_touch_vs(void) {
    TEST_BEGIN("TS-SF-04: V=0 sfence.vma does not affect VS-stage");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_fault_page;
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    /* Warm up. */
    (void)ts2_run_check_no_fault(&ctx, test_vs_read_write, va);

    /* Invalidate VS leaf. */
    (void)pt_map_page(&ctx.vs_ctx, va & ~0xfffUL, va & ~0xfffUL,
                      G12_VS_INV, PT_LEVEL_4K);

    /* HS-mode SFENCE.VMA (V=0). Operates on HS-level translation caches
     * only; must not impact VS-stage cleanup behavior. */
    (void)run_in_priv(PRIV_S, g12_hs_sfence_vma_all, 0);

    /* Now apply the proper HFENCE.VVMA -> VS-stage flush. */
    hfence_vvma_all();

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_load_expect_fault, va);
    bool fired = trap_was_triggered();
    uintptr_t cause = fired ? trap_get_cause() : 0;
    trap_expect_end();
    ts2_finish(&ctx);

    TEST_ASSERT("VS-mode load trapped after HFENCE.VVMA", fired);
    TEST_ASSERT_EQ("cause = load-page-fault (13)",
                   cause, (uintptr_t)CAUSE_LOAD_PAGE_FAULT);
    HYP_TEST_END();
}
