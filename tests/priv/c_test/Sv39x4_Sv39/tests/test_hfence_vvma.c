/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * common/hyp/tests_2stage/test_group10_hfence_vvma.c
 *
 * Group 10 - HFENCE.VVMA semantics (TS-HV-01..06)
 *
 * Spec basis:
 *   - HFENCE.VVMA flushes VS-stage translation caches; without it the
 *     TLB may continue to use stale VS-stage entries.
 *   - rs1=x0/rs2=x0 -> global; rs1!=0 -> by VA; rs2!=0 -> by ASID.
 *   - Valid in M-mode and HS-mode.
 *   - mstatus.TVM and hstatus.VTVM do NOT trap HFENCE.VVMA in HS-mode.
 *   - Executing HFENCE.VVMA when V=1 -> virtual-instruction exception
 *     (cause=22). Executing in U-mode -> illegal-instruction (cause=2).
 * =================================================================== */

#ifndef SUITE_HGATP_MODE
#error "SUITE_HGATP_MODE must be defined before including this file"
#endif
#ifndef SUITE_VSATP_MODE
#error "SUITE_VSATP_MODE must be defined before including this file"
#endif


#define G10_VS_RWX  (PTE_V|PTE_R|PTE_W|PTE_X|PTE_A|PTE_D)
#define G10_VS_INV  (0)

extern uintptr_t run_in_priv(unsigned priv,
                             uintptr_t (*fn)(uintptr_t), uintptr_t arg);

/* HS-mode helper: HFENCE.VVMA all. Returns 0. */
static uintptr_t g10_hs_hfence_vvma_all(uintptr_t arg) {
    (void)arg;
    asm volatile (".word 0x22000073" ::: "memory");  /* hfence.vvma x0,x0 */
    return 0;
}

/* VS-mode helper: HFENCE.VVMA all -> expected to raise virtual-inst. */
static uintptr_t g10_vs_hfence_vvma_all(uintptr_t arg) {
    (void)arg;
    asm volatile (".word 0x22000073" ::: "memory");
    return 0;
}

/* Common helper: rewrite the VS-stage 4K leaf for @va to @flags, then
 * issue the requested HFENCE variant, then return the cause observed
 * during a VS-mode load to @va (0 if no fault). */
static uintptr_t g10_invalidate_then_hfence_then_load(
        two_stage_ctx_t *ctx, uintptr_t va,
        void (*fence_fn)(uintptr_t va, uintptr_t asid),
        uintptr_t fence_va, uintptr_t fence_asid)
{
    /* Rewrite VS leaf to V=0. */
    (void)pt_map_page(&ctx->vs_ctx, va & ~0xfffUL, va & ~0xfffUL,
                      G10_VS_INV, PT_LEVEL_4K);
    /* Issue HFENCE.VVMA per the variant requested. */
    fence_fn(fence_va, fence_asid);

    trap_expect_begin();
    (void)two_stage_run_in_vs(ctx, test_vs_load_expect_fault, va);
    bool fired = trap_was_triggered();
    uintptr_t cause = fired ? trap_get_cause() : 0;
    trap_expect_end();
    return cause;
}

/* Adapter to fit hfence_vvma_all into the (va,asid) signature. */
static void g10_hfence_all_adapter(uintptr_t va, uintptr_t asid) {
    (void)va; (void)asid;
    hfence_vvma_all();
}

/* ===================================================================
 * TS-HV-01: rs1=0/rs2=0 global flush -> new PTE visible.
 * =================================================================== */
TEST_REGISTER(test_ts_hv_01_global);
bool test_ts_hv_01_global(void) {
    TEST_BEGIN("TS-HV-01: hfence.vvma x0,x0 -> new PTE visible");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_fault_page;
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    /* Warm up: first access succeeds. */
    (void)ts2_run_check_no_fault(&ctx, test_vs_read_write, va);

    uintptr_t cause = g10_invalidate_then_hfence_then_load(
            &ctx, va, g10_hfence_all_adapter, 0, 0);
    ts2_finish(&ctx);
    TEST_ASSERT_EQ("cause = load-page-fault (13) [new PTE visible]",
                   cause, (uintptr_t)CAUSE_LOAD_PAGE_FAULT);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-HV-02: hfence.vvma vaddr,x0 (per-VA) -> new PTE visible.
 * =================================================================== */
TEST_REGISTER(test_ts_hv_02_by_va);
bool test_ts_hv_02_by_va(void) {
    TEST_BEGIN("TS-HV-02: hfence.vvma vaddr,x0 -> new PTE visible");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_fault_page;
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);
    (void)ts2_run_check_no_fault(&ctx, test_vs_read_write, va);

    uintptr_t cause = g10_invalidate_then_hfence_then_load(
            &ctx, va, hfence_vvma, va, 0);
    ts2_finish(&ctx);
    TEST_ASSERT_EQ("cause = load-page-fault (13) [per-VA flush effective]",
                   cause, (uintptr_t)CAUSE_LOAD_PAGE_FAULT);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-HV-03: hfence.vvma x0,asid (per-ASID) -> new PTE visible.
 * Our setup uses asid=0; spec says asid=0 still flushes the asid=0
 * subset which is exactly what we use.
 * =================================================================== */
TEST_REGISTER(test_ts_hv_03_by_asid);
bool test_ts_hv_03_by_asid(void) {
    TEST_BEGIN("TS-HV-03: hfence.vvma x0,asid -> new PTE visible");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_fault_page;
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);
    (void)ts2_run_check_no_fault(&ctx, test_vs_read_write, va);

    /* hfence.vvma x0, asid=0 (our default vsatp.ASID). spec: when
     * rs1=x0 and rs2!=x0, only ASID-tagged entries for the supplied
     * ASID are flushed. */
    uintptr_t cause = g10_invalidate_then_hfence_then_load(
            &ctx, va, hfence_vvma, 0, /*asid*/0);
    ts2_finish(&ctx);
    TEST_ASSERT_EQ("cause = load-page-fault (13) [per-ASID flush effective]",
                   cause, (uintptr_t)CAUSE_LOAD_PAGE_FAULT);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-HV-04: mstatus.TVM=1 must NOT trap HFENCE.VVMA in HS-mode.
 * =================================================================== */
TEST_REGISTER(test_ts_hv_04_tvm_no_trap);
bool test_ts_hv_04_tvm_no_trap(void) {
    TEST_BEGIN("TS-HV-04: mstatus.TVM=1 does not trap HFENCE.VVMA in HS");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    /* Set mstatus.TVM=1 (bit 20). TVM is a configuration bit (not an
     * xret return-path bit), so the adaptive accessor proxies it
     * safely from HS-mode via T-SBI. */
    tsbi_csr_set(CSR_MSTATUS, MSTATUS_TVM);

    trap_expect_begin();
    (void)run_in_priv(PRIV_S, g10_hs_hfence_vvma_all, 0);
    bool fired = trap_was_triggered();
    trap_expect_end();

    /* Restore mstatus.TVM=0 to avoid leaking state. */
    tsbi_csr_clear(CSR_MSTATUS, MSTATUS_TVM);

    TEST_ASSERT("HFENCE.VVMA in HS with TVM=1 raised no trap", !fired);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-HV-05: hstatus.VTVM=1 must NOT trap HFENCE.VVMA in HS-mode.
 * =================================================================== */
TEST_REGISTER(test_ts_hv_05_vtvm_no_trap);
bool test_ts_hv_05_vtvm_no_trap(void) {
    TEST_BEGIN("TS-HV-05: hstatus.VTVM=1 does not trap HFENCE.VVMA in HS");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    /* Set hstatus.VTVM=1 (bit 20). */
    CSRS(CSR_HSTATUS, (uintptr_t)HSTATUS_VTVM);

    trap_expect_begin();
    (void)run_in_priv(PRIV_S, g10_hs_hfence_vvma_all, 0);
    bool fired = trap_was_triggered();
    trap_expect_end();

    CSRC(CSR_HSTATUS, (uintptr_t)HSTATUS_VTVM);

    TEST_ASSERT("HFENCE.VVMA in HS with VTVM=1 raised no trap", !fired);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-HV-06: HFENCE.VVMA in V=1 -> virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(test_ts_hv_06_v1_virt_inst);
bool test_ts_hv_06_v1_virt_inst(void) {
    TEST_BEGIN("TS-HV-06: HFENCE.VVMA in VS-mode -> virt-inst (22)");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, g10_vs_hfence_vvma_all, 0);
    bool fired = trap_was_triggered();
    uintptr_t cause = fired ? trap_get_cause() : 0;
    trap_expect_end();
    ts2_finish(&ctx);

    TEST_ASSERT("trap fired in VS-mode", fired);
    TEST_ASSERT_EQ("cause = virtual-instruction (22)",
                   cause, (uintptr_t)CAUSE_VIRTUAL_INSTRUCTION);
    HYP_TEST_END();
}
