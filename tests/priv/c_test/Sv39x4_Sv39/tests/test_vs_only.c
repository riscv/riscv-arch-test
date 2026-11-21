/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * common/hyp/tests_2stage/test_group01_vs_only.c
 *
 * Group 1: VS-stage only (hgatp = Bare)
 *
 * When hgatp.MODE == Bare, the second-stage translation is the
 * identity, so the only translation in effect is the VS-stage walked
 * by vsatp. VS-stage faults therefore raise a regular page-fault
 * (cause 12/13/15), NOT a guest-page-fault.
 *
 * Cases (test_plan: TS-VS-01..10):
 *   TS-VS-01  vsatp=Sv39, 4K identity, read+write succeeds
 *   TS-VS-02  vsatp=Sv39, 2MB superpage succeeds
 *   TS-VS-03  vsatp=Sv39, 1GB superpage succeeds
 *   TS-VS-04  vsatp=Sv48, 4K identity succeeds
 *   TS-VS-05  vsatp=Sv57, 4K identity succeeds
 *   TS-VS-06  VS-stage U=0 (S-level) read succeeds
 *   TS-VS-07  VS-stage U=1 + SUM=0                 -> load-page-fault
 *   TS-VS-08  VS-stage U=1 + SUM=1                 -> success
 *   TS-VS-09  VS-stage MXR=1 + X-only              -> success (readable)
 *   TS-VS-10  VS-stage R-only + store              -> store-page-fault
 *
 * This file is intended to be #include'd by a per-suite
 * tests/test_register.c that has previously defined SUITE_VSATP_MODE
 * if needed (default Sv39 from the framework header).
 *
 * The file does NOT use printf inside VS-mode; all UART output is
 * issued from M-mode after the inner trampoline returns.
 * =================================================================== */

#include "two_stage_helpers.h"

/* ----- helpers ----- */

/* All Group 1 cases run with G-stage disabled (hgatp.MODE=Bare). */

/* U=1 flags for VS-stage (SUM tests). */
#define G1_VS_RWXU_AD  (PTE_V|PTE_R|PTE_W|PTE_X|PTE_U|PTE_A|PTE_D)
/* X-only S-level (U=0) for MXR test: U must be 0 so the S-level
 * access is not rejected by the U-bit check before MXR can apply. */
#define G1_VS_X_AD     (PTE_V|PTE_X|PTE_A|PTE_D)


/* File-scope SUM choice: uses shared g_vs_sum_value / vs_load_with_sum
 * from test_helpers.h. */

/* ===================================================================
 * TS-VS-01: vsatp=Sv39, 4K identity, simple R/W cycle
 * =================================================================== */
TEST_REGISTER(test_ts_vs_01_sv39_4k);
bool test_ts_vs_01_sv39_4k(void)
{
    TEST_BEGIN("TS-VS-01: vsatp=Sv39 4K identity, R/W succeeds");
    REQUIRE_VSATP_MODE(SATP_MODE_SV39);

    two_stage_ctx_t ctx;
    ts2_setup_full(&ctx, SATP_MODE_SV39, HGATP_MODE_BARE);

    uintptr_t va = (uintptr_t)test_data_area;
    uintptr_t r = ts2_run_check_no_fault(&ctx, test_vs_read_write, va);
    TEST_ASSERT_EQ("read-back equals magic", r, 0);

    ts2_finish(&ctx);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-VS-02: vsatp=Sv39, 2MB superpage covers test region
 * =================================================================== */
TEST_REGISTER(test_ts_vs_02_sv39_2m);
bool test_ts_vs_02_sv39_2m(void)
{
    TEST_BEGIN("TS-VS-02: vsatp=Sv39 2MB superpage");
    REQUIRE_VSATP_MODE(SATP_MODE_SV39);

    two_stage_ctx_t ctx;
    /* Manual setup: skip the framework's default 4K mapping and use
     * a single 2MB leaf for the test region. */
    gpt_pool_reset();
    pt_pool_reset();
    two_stage_init(&ctx, SATP_MODE_SV39, HGATP_MODE_BARE);

    uintptr_t base2m = TEST_REGION_BASE & ~(PAGE_SIZE_2M - 1);
    /* Identity-map low memory + the test 2MB superpage. */
    for (uintptr_t a = (PLATFORM_MEM_BASE & ~(PAGE_SIZE_2M - 1));
         a < base2m;
         a += PAGE_SIZE_2M) {
        (void)pt_map_page(&ctx.vs_ctx, a, a, VS_FLAGS_RWX_S_AD,
                          PT_LEVEL_2M);
    }
    (void)pt_map_page(&ctx.vs_ctx, base2m, base2m,
                      VS_FLAGS_RWX_S_AD, PT_LEVEL_2M);

    uintptr_t va = (uintptr_t)test_data_area;
    uintptr_t r = ts2_run_check_no_fault(&ctx, test_vs_read_write, va);
    TEST_ASSERT_EQ("read-back equals magic", r, 0);

    ts2_finish(&ctx);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-VS-03: vsatp=Sv39, 1GB superpage at low memory
 * =================================================================== */
TEST_REGISTER(test_ts_vs_03_sv39_1g);
bool test_ts_vs_03_sv39_1g(void)
{
    TEST_BEGIN("TS-VS-03: vsatp=Sv39 1GB superpage");
    REQUIRE_VSATP_MODE(SATP_MODE_SV39);

    two_stage_ctx_t ctx;
    gpt_pool_reset();
    pt_pool_reset();
    two_stage_init(&ctx, SATP_MODE_SV39, HGATP_MODE_BARE);

    /* Identity-map a single 1GB region that covers code, UART, and
     * the test region. PLATFORM_MEM_BASE is 0x80000000 -> 1GB = [0x80000000, 0xC0000000). */
    uintptr_t base1g = PLATFORM_MEM_BASE & ~(PAGE_SIZE_1G - 1);
    (void)pt_map_page(&ctx.vs_ctx, base1g, base1g,
                      VS_FLAGS_RWX_S_AD, PT_LEVEL_1G);

    uintptr_t va = (uintptr_t)test_data_area;
    uintptr_t r = ts2_run_check_no_fault(&ctx, test_vs_read_write, va);
    TEST_ASSERT_EQ("read-back equals magic", r, 0);

    ts2_finish(&ctx);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-VS-04: vsatp=Sv48, 4K identity
 * =================================================================== */
TEST_REGISTER(test_ts_vs_04_sv48_4k);
bool test_ts_vs_04_sv48_4k(void)
{
    TEST_BEGIN("TS-VS-04: vsatp=Sv48 4K identity");
    REQUIRE_VSATP_MODE(SATP_MODE_SV48);

    two_stage_ctx_t ctx;
    ts2_setup_full(&ctx, SATP_MODE_SV48, HGATP_MODE_BARE);

    uintptr_t va = (uintptr_t)test_data_area;
    uintptr_t r = ts2_run_check_no_fault(&ctx, test_vs_read_write, va);
    TEST_ASSERT_EQ("read-back equals magic", r, 0);

    ts2_finish(&ctx);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-VS-05: vsatp=Sv57, 4K identity
 * =================================================================== */
TEST_REGISTER(test_ts_vs_05_sv57_4k);
bool test_ts_vs_05_sv57_4k(void)
{
    TEST_BEGIN("TS-VS-05: vsatp=Sv57 4K identity");
    REQUIRE_VSATP_MODE(SATP_MODE_SV57);

    two_stage_ctx_t ctx;
    ts2_setup_full(&ctx, SATP_MODE_SV57, HGATP_MODE_BARE);

    uintptr_t va = (uintptr_t)test_data_area;
    uintptr_t r = ts2_run_check_no_fault(&ctx, test_vs_read_write, va);
    TEST_ASSERT_EQ("read-back equals magic", r, 0);

    ts2_finish(&ctx);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-VS-06: VS-stage U=0 + S-level (VS-mode) access succeeds
 * =================================================================== */
TEST_REGISTER(test_ts_vs_06_ubit_s_level_ok);
bool test_ts_vs_06_ubit_s_level_ok(void)
{
    TEST_BEGIN("TS-VS-06: VS-stage U=0 + S-level access OK");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);

    two_stage_ctx_t ctx;
    /* Default VS_FLAGS_RWX_S_AD has U=0; ts2_setup_full installs it. */
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, HGATP_MODE_BARE);

    uintptr_t va = (uintptr_t)test_data_area;
    uintptr_t r = ts2_run_check_no_fault(&ctx, test_vs_read_write, va);
    TEST_ASSERT_EQ("S-level access succeeds", r, 0);

    ts2_finish(&ctx);
    HYP_TEST_END();
}

/* VS-mode helper: simple load (for MXR test where store is not allowed).
 * MXR is pre-set by the M-mode caller before entering VS-mode. */
static uintptr_t g1_vs_simple_load(uintptr_t va) {
    volatile uint64_t *p = (volatile uint64_t *)va;
    return (uintptr_t)(*p);
}

/* ===================================================================
 * TS-VS-07: VS-stage U=1 + SUM=0 -> load page-fault (cause 13)
 *
 * Spec: VS-mode (S-level) cannot access a U=1 PTE when
 * vsstatus.SUM=0. With hgatp=Bare, this is a regular page-fault,
 * not a guest-page-fault.
 * =================================================================== */
TEST_REGISTER(test_ts_vs_07_u1_sum0_fault);
bool test_ts_vs_07_u1_sum0_fault(void)
{
    TEST_BEGIN("TS-VS-07: VS U=1 + SUM=0 -> load-page-fault");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_fault_page;
    /* VS-stage PTE U=1, hgatp=Bare. */
    ts2_setup_with_vs_victim(&ctx, SUITE_VSATP_MODE, HGATP_MODE_BARE,
                             va, G1_VS_RWXU_AD);

    g_vs_sum_value = 0;
    bool ok = ts2_run_check_fault(&ctx, vs_load_with_sum, va,
                                  CAUSE_LOAD_PAGE_FAULT);
    TEST_ASSERT("load-page-fault on U=1 + SUM=0", ok);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-VS-08: VS-stage U=1 + SUM=1 -> success
 *
 * Spec: vsstatus.SUM=1 permits VS-mode (S-level) to access U=1 PTEs.
 * =================================================================== */
TEST_REGISTER(test_ts_vs_08_u1_sum1_ok);
bool test_ts_vs_08_u1_sum1_ok(void)
{
    TEST_BEGIN("TS-VS-08: VS U=1 + SUM=1 -> success");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_fault_page;
    ts2_setup_with_vs_victim(&ctx, SUITE_VSATP_MODE, HGATP_MODE_BARE,
                             va, G1_VS_RWXU_AD);

    g_vs_sum_value = 1;
    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, vs_load_with_sum, va);
    bool fired = trap_was_triggered();
    trap_expect_end();
    ts2_finish(&ctx);
    TEST_ASSERT("no fault (SUM=1 permits VS->U access)", !fired);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-VS-09: VS-stage MXR=1 + X-only -> success (readable)
 *
 * Spec (norm:vsstatus_mxr_vm): vsstatus.MXR makes execute-only
 * pages readable by explicit loads. With hgatp=Bare, there is no
 * G-stage to override; only VS-stage MXR applies.
 * =================================================================== */
TEST_REGISTER(test_ts_vs_09_mxr_xonly_ok);
bool test_ts_vs_09_mxr_xonly_ok(void)
{
    TEST_BEGIN("TS-VS-09: VS MXR=1 + X-only -> readable");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_fault_page;
    /* VS-stage X-only (R=0, W=0, X=1), U=0 (S-level access).
     * Use dual_victim to set both VS-stage and G-stage explicitly,
     * matching the proven Group 8 MXR test pattern (G8_VS_X). */
    ts2_setup_with_dual_victim(&ctx, SUITE_VSATP_MODE, HGATP_MODE_BARE,
                                va, G1_VS_X_AD, G_FLAGS_RWXU_AD);

    /* Enable vsstatus.MXR=1, clear sstatus.MXR=0.
     * Per norm:vsstatus_mxr_vm, vsstatus.MXR overrides VS-stage
     * execute-only. This exactly mirrors the TS-MXR-02 pattern
     * which is known to pass. */
    CSRC(CSR_SSTATUS, (uintptr_t)SSTATUS_MXR_BIT);
    CSRS(CSR_VSSTATUS, (uintptr_t)SSTATUS_MXR_BIT);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, g1_vs_simple_load, va);
    bool fired = trap_was_triggered();
    trap_expect_end();

    CSRC(CSR_SSTATUS, (uintptr_t)SSTATUS_MXR_BIT);
    CSRC(CSR_VSSTATUS, (uintptr_t)SSTATUS_MXR_BIT);
    ts2_finish(&ctx);
    TEST_ASSERT("vsstatus.MXR=1 makes VS X-only readable", !fired);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-VS-10: VS-stage R-only + store -> store page-fault
 * =================================================================== */
TEST_REGISTER(test_ts_vs_10_pte_ronly_store);
bool test_ts_vs_10_pte_ronly_store(void)
{
    TEST_BEGIN("TS-VS-10: VS-stage R-only + store -> page-fault");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_fault_page;
    uintptr_t bad_flags = PTE_V | PTE_R | PTE_A | PTE_D;  /* no W */
    ts2_setup_with_vs_victim(&ctx, SUITE_VSATP_MODE, HGATP_MODE_BARE,
                             va, bad_flags);

    bool ok = ts2_run_check_fault(&ctx, test_vs_store_expect_fault, va,
                                  CAUSE_STORE_PAGE_FAULT);
    TEST_ASSERT("store-page-fault on R-only", ok);
    HYP_TEST_END();
}
