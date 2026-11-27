/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * common/hyp/tests_2stage/test_group08_mxr.c
 *
 * Group 8 - MXR semantics across the two stages (TS-MXR-01..05)
 *
 * Spec basis:
 *   - vsstatus.MXR (VS-level): only overrides VS-stage execute-only
 *     pages, NOT G-stage execute-only pages.
 *   - sstatus.MXR (HS-level): overrides BOTH VS-stage and G-stage
 *     execute-only pages.
 *   - "Execute-only" here = X=1, R=0 leaf PTE; with MXR=1 the load
 *     is permitted as if R=1.
 *
 * Convention:
 *   - sstatus.MXR is written from M-mode. sstatus is the HS-level
 *     supervisor status register; its MXR bit governs HS/VS access
 *     to X-only pages when V=1.
 *   - vsstatus.MXR is written via CSR 0x200 from M-mode (or via
 *     `csrs sstatus` from VS-mode, which writes vsstatus when V=1).
 * =================================================================== */

#ifndef SUITE_HGATP_MODE
#error "SUITE_HGATP_MODE must be defined before including this file"
#endif
#ifndef SUITE_VSATP_MODE
#error "SUITE_VSATP_MODE must be defined before including this file"
#endif


/* PTE flag bundles. */
#define G8_VS_X       (PTE_V        |PTE_X  |PTE_A|PTE_D)        /* X-only S */
#define G8_VS_RWX     (PTE_V|PTE_R|PTE_W|PTE_X|PTE_A|PTE_D)
#define G8_G_RWXU     (PTE_V|PTE_R|PTE_W|PTE_X|PTE_U|PTE_A|PTE_D)
#define G8_G_XU       (PTE_V        |PTE_X  |PTE_U|PTE_A|PTE_D)  /* X-only U */

/* Plain VS-mode load helper: returns the loaded value if successful,
 * or 0 if the M-mode trap handler skipped over the faulting load.
 * Trap cause is queryable via trap_get_cause(). */
static uintptr_t g8_vs_load(uintptr_t va) {
    volatile uint64_t *p = (volatile uint64_t *)va;
    return (uintptr_t)(*p);
}

/* MXR control helpers — delegate to framework. */
static inline void g8_set_sstatus_mxr(int v)  { ts2_set_sstatus_mxr(v); }
static inline void g8_set_vsstatus_mxr(int v) { ts2_set_vsstatus_mxr(v); }

/* Run @fn in VS-mode and return (fired, cause) via out-params after
 * cleaning up two-stage state. */
static void g8_run_capture(two_stage_ctx_t *ctx,
                           uintptr_t (*fn)(uintptr_t), uintptr_t arg,
                           bool *out_fired, uintptr_t *out_cause)
{
    trap_expect_begin();
    (void)two_stage_run_in_vs(ctx, fn, arg);
    *out_fired = trap_was_triggered();
    *out_cause = *out_fired ? trap_get_cause() : 0;
    trap_expect_end();
    /* Clear MXR bits so subsequent tests start from a clean slate. */
    g8_set_sstatus_mxr(0);
    g8_set_vsstatus_mxr(0);
    ts2_finish(ctx);
}

/* ===================================================================
 * TS-MXR-01: VS X-only, G RWXU, MXR=0/0; load -> VS load-page-fault.
 * =================================================================== */
TEST_REGISTER(test_ts_mxr_01_no_mxr);
bool test_ts_mxr_01_no_mxr(void) {
    TEST_BEGIN("TS-MXR-01: VS X-only + no MXR -> page-fault (13)");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_fault_page;
    ts2_setup_with_dual_victim(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE, va,
                               G8_VS_X, G8_G_RWXU);
    g8_set_sstatus_mxr(0);
    g8_set_vsstatus_mxr(0);

    bool fired; uintptr_t cause;
    g8_run_capture(&ctx, g8_vs_load, va, &fired, &cause);
    TEST_ASSERT("trap fired", fired);
    TEST_ASSERT_EQ("cause = load-page-fault (13)",
                   cause, (uintptr_t)CAUSE_LOAD_PAGE_FAULT);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-MXR-02: VS X-only, G RWXU, vsstatus.MXR=1; load -> success.
 * =================================================================== */
TEST_REGISTER(test_ts_mxr_02_vs_mxr);
bool test_ts_mxr_02_vs_mxr(void) {
    TEST_BEGIN("TS-MXR-02: VS X-only + vsstatus.MXR=1 -> success");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_fault_page;
    ts2_setup_with_dual_victim(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE, va,
                               G8_VS_X, G8_G_RWXU);
    g8_set_sstatus_mxr(0);
    g8_set_vsstatus_mxr(1);

    bool fired; uintptr_t cause;
    g8_run_capture(&ctx, g8_vs_load, va, &fired, &cause);
    TEST_ASSERT("no fault (vsstatus.MXR overrides VS X-only)", !fired);
    (void)cause;
    HYP_TEST_END();
}

/* ===================================================================
 * TS-MXR-03: VS RWX, G X-only U, vsstatus.MXR=1; load -> guest-page-fault.
 * vsstatus.MXR must NOT cover G-stage execute-only.
 * =================================================================== */
TEST_REGISTER(test_ts_mxr_03_vs_mxr_no_g);
bool test_ts_mxr_03_vs_mxr_no_g(void) {
    TEST_BEGIN("TS-MXR-03: vsstatus.MXR cannot override G X-only");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_fault_page;
    ts2_setup_with_dual_victim(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE, va,
                               G8_VS_RWX, G8_G_XU);
    g8_set_sstatus_mxr(0);
    g8_set_vsstatus_mxr(1);

    bool fired; uintptr_t cause;
    g8_run_capture(&ctx, g8_vs_load, va, &fired, &cause);
    TEST_ASSERT("trap fired", fired);
    TEST_ASSERT_EQ("cause = load-guest-page-fault (21)",
                   cause, (uintptr_t)CAUSE_LOAD_GUEST_PAGE_FAULT);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-MXR-04: VS X-only, G X-only U, sstatus.MXR=1, vsstatus.MXR=0;
 * load -> success (HS-level MXR overrides both stages).
 * =================================================================== */
TEST_REGISTER(test_ts_mxr_04_hs_mxr);
bool test_ts_mxr_04_hs_mxr(void) {
    TEST_BEGIN("TS-MXR-04: sstatus.MXR=1 overrides both stages");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_fault_page;
    ts2_setup_with_dual_victim(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE, va,
                               G8_VS_X, G8_G_XU);
    g8_set_sstatus_mxr(1);
    g8_set_vsstatus_mxr(0);

    bool fired; uintptr_t cause;
    g8_run_capture(&ctx, g8_vs_load, va, &fired, &cause);
    TEST_ASSERT("no fault (sstatus.MXR overrides VS+G X-only)", !fired);
    (void)cause;
    HYP_TEST_END();
}

/* ===================================================================
 * TS-MXR-05: VS X-only, G X-only U, sstatus.MXR=1, vsstatus.MXR=1;
 * load -> success (equivalent to TS-MXR-04).
 * =================================================================== */
TEST_REGISTER(test_ts_mxr_05_both_mxr);
bool test_ts_mxr_05_both_mxr(void) {
    TEST_BEGIN("TS-MXR-05: sstatus.MXR + vsstatus.MXR both = 1 -> success");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_fault_page;
    ts2_setup_with_dual_victim(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE, va,
                               G8_VS_X, G8_G_XU);
    g8_set_sstatus_mxr(1);
    g8_set_vsstatus_mxr(1);

    bool fired; uintptr_t cause;
    g8_run_capture(&ctx, g8_vs_load, va, &fired, &cause);
    TEST_ASSERT("no fault (both MXR bits set)", !fired);
    (void)cause;
    HYP_TEST_END();
}
