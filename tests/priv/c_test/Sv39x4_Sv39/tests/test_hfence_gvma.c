/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * common/hyp/tests_2stage/test_group11_hfence_gvma.c
 *
 * Group 11 - HFENCE.GVMA semantics (TS-HG-01..06)
 *
 * Spec basis:
 *   - HFENCE.GVMA flushes G-stage translation caches.
 *   - rs1 (when non-zero) is the GPA shifted right by 2.
 *   - rs2 (when non-zero) selects a VMID.
 *   - Valid in M-mode and HS-mode (mstatus.TVM=0); in HS-mode with
 *     TVM=1 it must raise illegal-instruction (cause=2).
 *   - Executing in V=1 -> virtual-instruction (cause=22).
 *   - After changing hgatp.MODE the implementation must execute
 *     HFENCE.GVMA to make new translations take effect.
 * =================================================================== */

#ifndef SUITE_HGATP_MODE
#error "SUITE_HGATP_MODE must be defined before including this file"
#endif
#ifndef SUITE_VSATP_MODE
#error "SUITE_VSATP_MODE must be defined before including this file"
#endif


#define G11_G_RWXU  (PTE_V|PTE_R|PTE_W|PTE_X|PTE_U|PTE_A|PTE_D)

extern uintptr_t run_in_priv(unsigned priv,
                             uintptr_t (*fn)(uintptr_t), uintptr_t arg);

/* HS-mode helpers. */
static uintptr_t g11_hs_hfence_gvma_all(uintptr_t arg) {
    (void)arg;
    asm volatile (".word 0x62000073" ::: "memory");  /* hfence.gvma x0,x0 */
    return 0;
}

/* VS-mode helper: HFENCE.GVMA -> virt-inst expected. */
static uintptr_t g11_vs_hfence_gvma_all(uintptr_t arg) {
    (void)arg;
    asm volatile (".word 0x62000073" ::: "memory");
    return 0;
}

/* Common: rewrite G-stage 4K leaf for @gpa to @flags, fence, then
 * VS-mode load and return cause. */
static uintptr_t g11_g_invalidate_then_fence_then_load(
        two_stage_ctx_t *ctx, uintptr_t gpa,
        void (*fence_fn)(uintptr_t a, uintptr_t b),
        uintptr_t fence_a, uintptr_t fence_b)
{
    /* Make the G-stage leaf V=0 via the framework helper (it splits
     * any covering 2M superpage). NOTE: ts2_g_override_4k itself
     * issues hfence_gvma_all. To avoid pre-fencing the test, we
     * manipulate the PTE directly here. */
    uintptr_t *pte = gpt_get_pte(&ctx->g_ctx, gpa & ~0xfffUL, PT_LEVEL_4K);
    if (pte == NULL) {
        /* Need to split first. Use the framework helper, which also
         * fences; that pre-fences ahead of our user-issued fence,
         * but the test still verifies that the cause is correct. */
        ts2_g_override_4k(ctx, gpa, 0);
    } else {
        *pte = 0;
    }
    fence_fn(fence_a, fence_b);

    trap_expect_begin();
    (void)two_stage_run_in_vs(ctx, test_vs_load_expect_fault, gpa);
    bool fired = trap_was_triggered();
    uintptr_t cause = fired ? trap_get_cause() : 0;
    trap_expect_end();
    return cause;
}

static void g11_hfence_all_adapter(uintptr_t a, uintptr_t b) {
    (void)a; (void)b;
    hfence_gvma_all();
}

/* ===================================================================
 * TS-HG-01: hfence.gvma x0,x0 -> new G-stage PTE visible.
 * =================================================================== */
TEST_REGISTER(test_ts_hg_01_global);
bool test_ts_hg_01_global(void) {
    TEST_BEGIN("TS-HG-01: hfence.gvma x0,x0 -> new G PTE visible");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_fault_page;
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);
    /* Warm. */
    (void)ts2_run_check_no_fault(&ctx, test_vs_read_write, va);

    uintptr_t cause = g11_g_invalidate_then_fence_then_load(
            &ctx, va, g11_hfence_all_adapter, 0, 0);
    ts2_finish(&ctx);
    TEST_ASSERT_EQ("cause = load-guest-page-fault (21)",
                   cause, (uintptr_t)CAUSE_LOAD_GUEST_PAGE_FAULT);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-HG-02: hfence.gvma gpa>>2, x0 -> per-GPA flush effective.
 * =================================================================== */
TEST_REGISTER(test_ts_hg_02_by_gpa);
bool test_ts_hg_02_by_gpa(void) {
    TEST_BEGIN("TS-HG-02: hfence.gvma gpa>>2, x0 -> per-GPA flush");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_fault_page;
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);
    (void)ts2_run_check_no_fault(&ctx, test_vs_read_write, va);

    uintptr_t cause = g11_g_invalidate_then_fence_then_load(
            &ctx, va, hfence_gvma, va >> 2, 0);
    ts2_finish(&ctx);
    TEST_ASSERT_EQ("cause = load-guest-page-fault (21)",
                   cause, (uintptr_t)CAUSE_LOAD_GUEST_PAGE_FAULT);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-HG-03: hfence.gvma x0, vmid -> per-VMID flush.
 * Our setup uses vmid=0; spec says the supplied VMID is matched.
 * =================================================================== */
TEST_REGISTER(test_ts_hg_03_by_vmid);
bool test_ts_hg_03_by_vmid(void) {
    TEST_BEGIN("TS-HG-03: hfence.gvma x0,vmid -> per-VMID flush");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_fault_page;
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);
    (void)ts2_run_check_no_fault(&ctx, test_vs_read_write, va);

    uintptr_t cause = g11_g_invalidate_then_fence_then_load(
            &ctx, va, hfence_gvma, 0, /*vmid*/0);
    ts2_finish(&ctx);
    TEST_ASSERT_EQ("cause = load-guest-page-fault (21)",
                   cause, (uintptr_t)CAUSE_LOAD_GUEST_PAGE_FAULT);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-HG-04: hgatp.MODE switch must be followed by HFENCE.GVMA.
 * We rebuild the suite with a different g_mode and verify access.
 * Sv39x4 suite: switch to Bare and back via hgatp_set + hfence.
 * =================================================================== */
TEST_REGISTER(test_ts_hg_04_mode_switch);
bool test_ts_hg_04_mode_switch(void) {
    TEST_BEGIN("TS-HG-04: hgatp.MODE switch + HFENCE.GVMA -> ok");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_fault_page;
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);
    (void)ts2_run_check_no_fault(&ctx, test_vs_read_write, va);

    /* Switch hgatp.MODE: temporarily go to Bare, fence, then restore. */
    CSRW(CSR_HGATP, 0);  /* hgatp = 0 (Bare) */
    hfence_gvma_all();
    /* Restore by re-enabling the same context. */
    {
        uintptr_t root_ppn = ((uintptr_t)ctx.g_ctx.root_pt) >> PAGE_SHIFT;
        uintptr_t new_hgatp = ((uintptr_t)SUITE_HGATP_MODE << 60) | root_ppn;
        CSRW(CSR_HGATP, new_hgatp);
        hfence_gvma_all();
    }
    /* Re-enable VS state and verify access still works. */
    CSRW(CSR_VSATP, 0);  /* vsatp=0 */
    {
        uintptr_t root_ppn = ((uintptr_t)ctx.vs_ctx.root_pt) >> PAGE_SHIFT;
        uintptr_t vsatp = MAKE_SATP(ctx.vs_ctx.mode, 0, root_ppn);
        CSRW(CSR_VSATP, vsatp);
        hfence_vvma_all();
    }
    uintptr_t r = ts2_run_check_no_fault(&ctx, test_vs_read_write, va);
    ts2_finish(&ctx);
    TEST_ASSERT("post-MODE-switch access succeeds", r == 0);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-HG-05: mstatus.TVM=1 in HS-mode -> illegal-instruction (cause=2).
 * =================================================================== */
TEST_REGISTER(test_ts_hg_05_tvm_illegal);
bool test_ts_hg_05_tvm_illegal(void) {
    TEST_BEGIN("TS-HG-05: TVM=1 in HS -> illegal-inst (2)");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    /* TVM is a configuration bit (not an xret return-path bit), so
     * the adaptive accessor proxies it safely from HS-mode via T-SBI. */
    tsbi_csr_set(CSR_MSTATUS, MSTATUS_TVM);

    trap_expect_begin();
    (void)run_in_priv(PRIV_S, g11_hs_hfence_gvma_all, 0);
    bool fired = trap_was_triggered();
    uintptr_t cause = fired ? trap_get_cause() : 0;
    trap_expect_end();

    tsbi_csr_clear(CSR_MSTATUS, MSTATUS_TVM);

    TEST_ASSERT("trap fired", fired);
    TEST_ASSERT_EQ("cause = illegal-instruction (2)",
                   cause, (uintptr_t)CAUSE_ILLEGAL_INST);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-HG-06: HFENCE.GVMA in V=1 -> virtual-instruction (cause=22).
 * =================================================================== */
TEST_REGISTER(test_ts_hg_06_v1_virt_inst);
bool test_ts_hg_06_v1_virt_inst(void) {
    TEST_BEGIN("TS-HG-06: HFENCE.GVMA in VS-mode -> virt-inst (22)");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, g11_vs_hfence_gvma_all, 0);
    bool fired = trap_was_triggered();
    uintptr_t cause = fired ? trap_get_cause() : 0;
    trap_expect_end();
    ts2_finish(&ctx);

    TEST_ASSERT("trap fired in VS-mode", fired);
    TEST_ASSERT_EQ("cause = virtual-instruction (22)",
                   cause, (uintptr_t)CAUSE_VIRTUAL_INSTRUCTION);
    HYP_TEST_END();
}
