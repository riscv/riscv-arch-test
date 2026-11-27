/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * common/hyp/tests_2stage/test_group07_perm_cross.c
 *
 * Group 7 - VS-stage RWX x G-stage RWX permission cross
 *           (TS-PERM-01..12)
 *
 * Spec basis:
 *   - Both stages must permit the access; either stage refusing it
 *     raises a fault.
 *   - Cause discriminates the source stage:
 *       VS-stage refuse  -> page-fault         (12 / 13 / 15)
 *       G-stage  refuse  -> guest-page-fault   (20 / 21 / 23)
 *
 * The framework helpers ts2_setup_with_vs_victim / _g_victim /
 * _dual_victim are used to install a single offending leaf PTE on
 * top of an otherwise identity-mapped layout.
 * =================================================================== */

#ifndef SUITE_HGATP_MODE
#error "SUITE_HGATP_MODE must be defined before including this file"
#endif
#ifndef SUITE_VSATP_MODE
#error "SUITE_VSATP_MODE must be defined before including this file"
#endif


/* Common reusable PTE flag bundles. AD bits set so we never trigger
 * an A/D-update fault that would mask the permission semantics. */
#define G7_VS_RWX     (PTE_V|PTE_R|PTE_W|PTE_X|PTE_A|PTE_D)        /* S-level */
#define G7_VS_R       (PTE_V|PTE_R          |PTE_A|PTE_D)
#define G7_VS_X       (PTE_V        |PTE_X  |PTE_A|PTE_D)
#define G7_VS_RX      (PTE_V|PTE_R  |PTE_X  |PTE_A|PTE_D)
#define G7_VS_INV     (0)
#define G7_VS_RWX_U   (PTE_V|PTE_R|PTE_W|PTE_X|PTE_U|PTE_A|PTE_D)  /* U-level */

#define G7_G_RWXU     (PTE_V|PTE_R|PTE_W|PTE_X|PTE_U|PTE_A|PTE_D)
#define G7_G_RU       (PTE_V|PTE_R          |PTE_U|PTE_A|PTE_D)
#define G7_G_XU       (PTE_V        |PTE_X  |PTE_U|PTE_A|PTE_D)
#define G7_G_RXU      (PTE_V|PTE_R  |PTE_X  |PTE_U|PTE_A|PTE_D)
#define G7_G_INV      (0)
#define G7_G_RWX_NOU  (PTE_V|PTE_R|PTE_W|PTE_X|PTE_A|PTE_D)        /* no U */

/* ===================================================================
 * TS-PERM-01: VS RWX, G RWXU - all access types succeed.
 * =================================================================== */
TEST_REGISTER(test_ts_perm_01_dual_rwx);
bool test_ts_perm_01_dual_rwx(void) {
    TEST_BEGIN("TS-PERM-01: dual RWX permits load+store");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);
    uintptr_t va = (uintptr_t)test_data_area;
    uintptr_t r = ts2_run_check_no_fault(&ctx, test_vs_read_write, va);
    TEST_ASSERT("read-modify-write succeeded", r == 0);
    ts2_finish(&ctx);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-PERM-02: VS R-only, G RWXU; store -> VS-stage store-page-fault.
 * Cause = 15 (store/AMO page-fault), VS-stage source.
 * =================================================================== */
TEST_REGISTER(test_ts_perm_02_vs_ronly_store);
bool test_ts_perm_02_vs_ronly_store(void) {
    TEST_BEGIN("TS-PERM-02: VS R-only + store -> VS page-fault (15)");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_fault_page;
    ts2_setup_with_vs_victim(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE, va, G7_VS_R);

    bool ok = ts2_run_check_fault(&ctx, test_vs_store_expect_fault, va,
                                  CAUSE_STORE_PAGE_FAULT);
    TEST_ASSERT("cause = store-page-fault (15) [VS-stage]", ok);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-PERM-03: VS RWX, G R-only U; store -> G-stage guest-page-fault.
 * Cause = 23, G-stage source.
 * =================================================================== */
TEST_REGISTER(test_ts_perm_03_g_ronly_store);
bool test_ts_perm_03_g_ronly_store(void) {
    TEST_BEGIN("TS-PERM-03: G R-only + store -> store-guest-page-fault (23)");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_fault_page;
    ts2_setup_with_g_victim(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE, va, G7_G_RU);

    bool ok = ts2_run_check_fault(&ctx, test_vs_store_expect_fault, va,
                                  CAUSE_STORE_GUEST_PAGE_FAULT);
    TEST_ASSERT("cause = store-guest-page-fault (23) [G-stage]", ok);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-PERM-04: VS X-only, G RWXU; load (no MXR) -> VS load-page-fault.
 * Cause = 13.
 * =================================================================== */
TEST_REGISTER(test_ts_perm_04_vs_xonly_load);
bool test_ts_perm_04_vs_xonly_load(void) {
    TEST_BEGIN("TS-PERM-04: VS X-only + load -> VS page-fault (13)");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_fault_page;
    ts2_setup_with_vs_victim(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE, va, G7_VS_X);

    bool ok = ts2_run_check_fault(&ctx, test_vs_load_expect_fault, va,
                                  CAUSE_LOAD_PAGE_FAULT);
    TEST_ASSERT("cause = load-page-fault (13) [VS-stage]", ok);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-PERM-05: VS RWX, G X-only U; load (no MXR) -> G load-guest-fault.
 * Cause = 21.
 * =================================================================== */
TEST_REGISTER(test_ts_perm_05_g_xonly_load);
bool test_ts_perm_05_g_xonly_load(void) {
    TEST_BEGIN("TS-PERM-05: G X-only + load -> load-guest-page-fault (21)");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_fault_page;
    ts2_setup_with_g_victim(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE, va, G7_G_XU);

    bool ok = ts2_run_check_fault(&ctx, test_vs_load_expect_fault, va,
                                  CAUSE_LOAD_GUEST_PAGE_FAULT);
    TEST_ASSERT("cause = load-guest-page-fault (21) [G-stage]", ok);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-PERM-06: VS RX, G RX U; fetch -> success.
 * =================================================================== */

/* Direct fetch helper: jalr to @arg, expecting normal return. We do
 * NOT use test_vs_exec_expect_fault here because that helper installs
 * an _exec_return_addr recovery anchor and trips trap_was_triggered()
 * even on the no-fault path (the trap recovery is for fault scenarios
 * only). The success path just calls a ret-only stub. */
static uintptr_t g7_vs_exec_no_fault(uintptr_t arg) {
    typedef void (*fn_t)(void);
    ((fn_t)arg)();
    return 0;
}

TEST_REGISTER(test_ts_perm_06_dual_rx_fetch);
bool test_ts_perm_06_dual_rx_fetch(void) {
    TEST_BEGIN("TS-PERM-06: dual RX permits fetch");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    /* test_exec_target backs a small ret-only stub written to RAM by
     * the suite startup. We only need to verify that fetching from it
     * does not fault. The page already lives in .vm_test_region.
     *
     * Override both stages to RX (no W). */
    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_exec_target;
    /* Plant a 16-bit `c.jr ra` (= 0x8082) at va so the fetch lands on
     * a real return instruction. test_exec_target lives in
     * .vm_test_region but has no static initializer, so without this
     * we'd fault with cause=2 (illegal instruction) on a zero word. */
    *(volatile uint16_t *)va = 0x8082;  /* c.jr ra */
    asm volatile ("fence.i" ::: "memory");
    ts2_setup_with_dual_victim(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE, va,
                               G7_VS_RX, G7_G_RXU);

    (void)ts2_run_check_no_fault(&ctx, g7_vs_exec_no_fault, va);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-PERM-07: VS V=0, G RWXU; load -> VS load-page-fault (13).
 * =================================================================== */
TEST_REGISTER(test_ts_perm_07_vs_invalid);
bool test_ts_perm_07_vs_invalid(void) {
    TEST_BEGIN("TS-PERM-07: VS V=0 + load -> VS page-fault (13)");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_fault_page;
    ts2_setup_with_vs_victim(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE, va, G7_VS_INV);

    bool ok = ts2_run_check_fault(&ctx, test_vs_load_expect_fault, va,
                                  CAUSE_LOAD_PAGE_FAULT);
    TEST_ASSERT("cause = load-page-fault (13) [VS V=0]", ok);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-PERM-08: VS RWX, G V=0; load -> G load-guest-page-fault (21).
 * =================================================================== */
TEST_REGISTER(test_ts_perm_08_g_invalid);
bool test_ts_perm_08_g_invalid(void) {
    TEST_BEGIN("TS-PERM-08: G V=0 + load -> guest-page-fault (21)");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_fault_page;
    ts2_setup_with_g_victim(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE, va, G7_G_INV);

    bool ok = ts2_run_check_fault(&ctx, test_vs_load_expect_fault, va,
                                  CAUSE_LOAD_GUEST_PAGE_FAULT);
    TEST_ASSERT("cause = load-guest-page-fault (21) [G V=0]", ok);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-PERM-09: VS RWX, G RWX (U=0); load -> G load-guest-page-fault.
 * G-stage treats every guest access as U-mode: U=0 forces fault.
 * =================================================================== */
TEST_REGISTER(test_ts_perm_09_g_no_u);
bool test_ts_perm_09_g_no_u(void) {
    TEST_BEGIN("TS-PERM-09: G U=0 + load -> guest-page-fault (21)");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_fault_page;
    ts2_setup_with_g_victim(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE, va, G7_G_RWX_NOU);

    bool ok = ts2_run_check_fault(&ctx, test_vs_load_expect_fault, va,
                                  CAUSE_LOAD_GUEST_PAGE_FAULT);
    TEST_ASSERT("cause = load-guest-page-fault (21) [G U=0]", ok);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-PERM-10: VS RWX (U=0), G RWXU; VU-mode load -> VS page-fault.
 * VU-mode is U-level guest: U=0 PTE forbids the access.
 * Cause = 13 (load-page-fault).
 * =================================================================== */
TEST_REGISTER(test_ts_perm_10_vs_no_u_vu);
bool test_ts_perm_10_vs_no_u_vu(void) {
    TEST_BEGIN("TS-PERM-10: VS U=0 + VU-mode load -> VS page-fault (13)");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_fault_page;
    /* VU-mode access requires VS-stage U=1 throughout. Use the U=1
     * variant of full setup, then override the victim page to U=0
     * (G7_VS_RWX without U). */
    ts2_setup_full_u(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);
    /* Force the victim page to U=0 in VS-stage. */
    (void)pt_map_page(&ctx.vs_ctx, va & ~0xfffUL, va & ~0xfffUL,
                      G7_VS_RWX, PT_LEVEL_4K);
    hfence_vvma_all();

    /* Route the expected page fault to HS, not VS. ts2_setup_full_u
     * maps the whole low-memory 2M superpages (holding ALL kernel
     * text) with U=1 so the VU-mode payload can execute; an S-level
     * VS trap handler can never fetch from U=1 pages (SUM gates data
     * only, never instruction fetch), so a fault delegated down to
     * the standing VS entry would make its very first fetch fault
     * again and re-delegate forever. Keep the cause at HS instead:
     * the HS handler runs on the bare HS satp and records into
     * trap_record, which the standard trap API observes below.
     * medeleg[13] stays set, so the VU fault still surfaces as a
     * genuine load-page-fault; only the serving level changes.
     * HYP_TEST_END restores the delegation baseline. */
    setup_deleg_to_hs(1UL << CAUSE_LOAD_PAGE_FAULT);

    trap_expect_begin();
    (void)two_stage_run_in_vu(&ctx, test_vs_load_expect_fault, va);
    bool fired = trap_was_triggered();
    uintptr_t cause = fired ? trap_get_cause() : 0;
    trap_expect_end();
    ts2_finish(&ctx);
    TEST_ASSERT("VU-mode access trapped", fired);
    TEST_ASSERT_EQ("cause = load-page-fault (13)",
                   cause, (uintptr_t)CAUSE_LOAD_PAGE_FAULT);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-PERM-11/12: VS U=1, G RWXU; VS-mode load with vsstatus.SUM = 0/1.
 *
 * SUM=0: VS-mode (S-level) cannot access U=1 page -> page-fault (13).
 * SUM=1: VS-mode can access U=1 page          -> success.
 *
 * vsstatus is the VS-mode view of sstatus, exposed at CSR 0x200.
 * SUM bit is bit 18 in sstatus / vsstatus (RV64).
 * =================================================================== */


/* SUM choice: uses shared g_vs_sum_value / vs_load_with_sum
 * from test_helpers.h. */

TEST_REGISTER(test_ts_perm_11_vs_u1_sum0);
bool test_ts_perm_11_vs_u1_sum0(void) {
    TEST_BEGIN("TS-PERM-11: VS U=1 + SUM=0 + VS load -> page-fault (13)");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_fault_page;
    /* VS U=1 victim; G default RWXU. */
    ts2_setup_with_vs_victim(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE, va, G7_VS_RWX_U);

    g_vs_sum_value = 0;
    bool ok = ts2_run_check_fault(&ctx, vs_load_with_sum, va,
                                  CAUSE_LOAD_PAGE_FAULT);
    TEST_ASSERT("cause = load-page-fault (13) [SUM=0 blocks]", ok);
    HYP_TEST_END();
}

TEST_REGISTER(test_ts_perm_12_vs_u1_sum1);
bool test_ts_perm_12_vs_u1_sum1(void) {
    TEST_BEGIN("TS-PERM-12: VS U=1 + SUM=1 + VS load -> success");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_fault_page;
    ts2_setup_with_vs_victim(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE, va, G7_VS_RWX_U);

    g_vs_sum_value = 1;
    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, vs_load_with_sum, va);
    bool fired = trap_was_triggered();
    trap_expect_end();
    ts2_finish(&ctx);
    TEST_ASSERT("no fault (SUM=1 permits VS->U access)", !fired);
    HYP_TEST_END();
}
