/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * common/hyp/tests_2stage/test_group19_pmp.c
 *
 * Group 19 - PMP interaction with two-stage translation
 * (TS-PMP-01).
 *
 * NOTE: TS-PMP-02 removed (framework cannot isolate G-stage root PMP deny).
 *
 * Spec basis (norm:H_pmp): Machine-level PMP applies to supervisor
 * physical addresses regardless of virtualization mode. Once both
 * VS-stage and G-stage succeed, the resulting SPA is still subject
 * to PMP; failure surfaces as access-fault (cause=5/7), NOT as a
 * page-fault or guest-page-fault.
 *
 * Strategy:
 *   - PMP entry 0 is the highest-priority entry (lowest index wins).
 *     The framework reset configures entry 0 = NAPOT covering the
 *     whole address space with RWX. We override entry 0 with a deny
 *     rule that matches the target page only, then add entry 1 as a
 *     fall-through NAPOT(all-space, RWX). VS-mode access to the
 *     target page hits entry 0 first -> deny.
 * =================================================================== */

#ifndef SUITE_HGATP_MODE
#error "SUITE_HGATP_MODE must be defined before including this file"
#endif
#ifndef SUITE_VSATP_MODE
#error "SUITE_VSATP_MODE must be defined before including this file"
#endif

#include "pmp/pmp_cfg.h"


/* PMP deny-window helpers from common/pmp/pmp_cfg.h. pmp_cfg.c
 * touches the M-only pmpcfg/pmpaddr registers through the thin
 * csr_read/csr_write accessors, so from this HS-mode suite it must run
 * inside an M-mode excursion; the PMP entries persist after we drop
 * back to the original privilege, so the subsequent VS-mode access
 * still hits the denial. (Shared pmp_cfg.c is deliberately left
 * untouched: its S-mode trap-probe semantics are load-bearing for the
 * entry-count/Smepmp detection used by other suites.) */
typedef pmp_save_t g19_pmp_save_t;

static void g19_pmp_deny_page(uintptr_t pa, g19_pmp_save_t *save) {
    unsigned saved = get_current_priv();
    if (saved != PRIV_M)
        goto_priv(PRIV_M);
    pmp_deny_page_4k(pa, save);
    if (saved != PRIV_M)
        goto_priv(saved);
}

static void g19_pmp_restore(const g19_pmp_save_t *save) {
    unsigned saved = get_current_priv();
    if (saved != PRIV_M)
        goto_priv(PRIV_M);
    pmp_restore(save);
    if (saved != PRIV_M)
        goto_priv(saved);
}

/* ===================================================================
 * TS-PMP-01: Two-stage translation succeeds, but the final SPA
 * is denied by PMP. Expect cause=5 (load-access-fault).
 * =================================================================== */
TEST_REGISTER(test_ts_pmp_01_spa_denied);
bool test_ts_pmp_01_spa_denied(void) {
    TEST_BEGIN("TS-PMP-01: PMP denies final SPA -> load-access-fault (5)");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_data_area;     /* identity == SPA */

    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    g19_pmp_save_t save;
    g19_pmp_deny_page(va, &save);

    bool ok = ts2_run_check_fault(&ctx, test_vs_load_expect_fault, va,
                                  CAUSE_LOAD_ACCESS_FAULT);
    g19_pmp_restore(&save);
    TEST_ASSERT("cause = load-access-fault (5)", ok);
    HYP_TEST_END();
}

/* TS-PMP-02: removed — denying G-stage root PMP also breaks the M->VS
 * trampoline path, making it impossible to isolate the fault. */
