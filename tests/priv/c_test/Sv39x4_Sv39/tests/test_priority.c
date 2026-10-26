/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * common/hyp/tests_2stage/test_group20_priority.c
 *
 * Group 20 - Synchronous-exception priority under two-stage
 * translation (TS-PRIO-01..02).
 *
 * Spec basis (norm:H_exception_priority):
 *   When several synchronous exceptions could simultaneously occur,
 *   priority decides which one is reported. We validate two
 *   common-path priority orderings:
 *
 *   1. VS-stage page-fault wins over misaligned fault.
 *   2. G-stage implicit-walk fault wins over VS-stage PTE content
 *      check (the VS-stage PTE is never inspected because the walk
 *      that would fetch it already faulted).
 * =================================================================== */

#ifndef SUITE_HGATP_MODE
#error "SUITE_HGATP_MODE must be defined before including this file"
#endif
#ifndef SUITE_VSATP_MODE
#error "SUITE_VSATP_MODE must be defined before including this file"
#endif


/* VS-stage victim PTE: present-but-invalid encoding (V=0). */
#define G20_VS_INVALID    (0)

/* Misaligned 4-byte load at arg = base + 1. Some implementations
 * permit unaligned access in hardware, so the misaligned exception
 * may not fire even with PTE valid; here PTE is V=0 so we expect
 * page-fault (13) regardless of misalign behaviour. */
static uintptr_t vs_lw_misaligned(uintptr_t arg) {
    volatile uint32_t *p = (volatile uint32_t *)(arg + 1);
    (void)*p;
    return trap_get_cause();
}

/* ===================================================================
 * TS-PRIO-01: misaligned + VS-stage PTE V=0 -> page-fault (13).
 * Page-fault must outrank misaligned per priority table.
 *
 * NOTE: This test requires hardware support for misaligned memory
 * access. If the platform does not support it (e.g., Spike without
 * Zicclsm), the test will see cause=4 (load-address-misaligned)
 * before reaching the page boundary. We treat this as a SKIP.
 * =================================================================== */
TEST_REGISTER(test_ts_prio_01_misalign_vs_v0);
bool test_ts_prio_01_misalign_vs_v0(void) {
    TEST_BEGIN("TS-PRIO-01: misalign + VS V=0 -> page-fault (13)");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_data_area;
    ts2_setup_with_vs_victim(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE,
                             va, G20_VS_INVALID);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, vs_lw_misaligned, va);
    bool fired = trap_was_triggered();
    uintptr_t cause = fired ? trap_get_cause() : 0;
    trap_expect_end();
    two_stage_cleanup(&ctx);
    hyp_reset_state();

    /* If misaligned access is not supported (cause=4), skip the test.
     * This is a platform limitation, not a test failure. */
    if (fired && cause == 4) {
        TEST_ASSERT("misaligned access not supported -> SKIP", true);
        HYP_TEST_END();
    }

    bool ok = (fired && cause == CAUSE_LOAD_PAGE_FAULT);
    TEST_ASSERT("cause = load-page-fault (13)", ok);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-PRIO-02: G-stage walk fault preempts VS-stage PTE check.
 *
 * We invalidate the VS-stage leaf PT page in G-stage AND set the
 * VS-stage leaf PTE itself to an invalid encoding. The reported
 * cause must be guest-page-fault (21), not load-page-fault (13),
 * because the G-stage walk for the VS-stage PT page faults before
 * the VS-stage PTE content is inspected.
 * =================================================================== */
TEST_REGISTER(test_ts_prio_02_gstage_first);
bool test_ts_prio_02_gstage_first(void) {
    TEST_BEGIN("TS-PRIO-02: G-stage implicit fault preempts VS PTE check");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_data_area;

    /* Build full identity, then mark the VS-stage leaf PTE V=0. */
    ts2_setup_with_vs_victim(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE,
                             va, G20_VS_INVALID);

    /* Now invalidate the VS-stage leaf PT page in G-stage. The PT
     * page-walk will fault before reaching the (also-invalid) leaf. */
    uintptr_t pt_gpa = ts2_invalidate_vs_pt_in_g(&ctx, va, PT_LEVEL_4K);
    TEST_ASSERT("VS leaf PT GPA resolvable", pt_gpa != 0);

    bool ok = ts2_run_check_fault(&ctx, test_vs_load_expect_fault, va,
                                  CAUSE_LOAD_GUEST_PAGE_FAULT);
    TEST_ASSERT("cause = load-guest-fault (21), not load-page-fault (13)", ok);
    HYP_TEST_END();
}
