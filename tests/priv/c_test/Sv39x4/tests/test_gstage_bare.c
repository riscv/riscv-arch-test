/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 14: hgatp MODE=Bare trivial translation (GBARE-01..05)
 *
 * Spec anchors:
 *   norm:hgatp_mode_bare_trans - with hgatp.MODE=Bare, guest physical
 *       addresses equal supervisor physical addresses without
 *       modification, and no memory protection applies in the trivial
 *       translation (a guest-page-fault can never occur).
 *   norm:hgatp_mode_bare       - no protection beyond PMP with Bare.
 *   norm:H_pmp                 - machine-level PMP applies to
 *       supervisor physical addresses regardless of V.
 *   norm:htval_trapval         - htval is zero for traps other than
 *       guest-page-fault.
 *   norm:hstatus_gva_op        - hstatus.GVA is 0 for traps that do
 *       not write a guest virtual address to stval.
 * =================================================================== */

#include "pmp/pmp_cfg.h"
#include "hyp/hyp_test_helpers.h"  /* setup_deleg_to_hs */

#define G14_BARE_VS  SATP_MODE_BARE
#define G14_BARE_G   HGATP_MODE_BARE

/* PMP deny-window helpers from common/pmp/pmp_cfg.h.
 *
 * pmpcfg and pmpaddr are M-level CSRs. Under the S(HS)-mode-normal boot
 * the test body runs in S-mode, where a direct pmpcfg/pmpaddr access
 * raises an illegal-instruction exception. Configure the deny window
 * inside an M-mode excursion; the PMP entries persist after we drop
 * back to the original privilege, so the subsequent VS-mode access
 * still hits the denial. */
typedef pmp_save_t g14_pmp_save_t;

static void g14_pmp_deny_page(uintptr_t pa, g14_pmp_save_t *save)
{
    unsigned saved = get_current_priv();
    if (saved != PRIV_M)
        goto_priv(PRIV_M);
    pmp_deny_page_4k(pa, save);
    if (saved != PRIV_M)
        goto_priv(saved);
}

static void g14_pmp_restore(const g14_pmp_save_t *save)
{
    unsigned saved = get_current_priv();
    if (saved != PRIV_M)
        goto_priv(PRIV_M);
    pmp_restore(save);
    if (saved != PRIV_M)
        goto_priv(saved);
}

/* norm:hgatp_mode_bare_trans: guest-page-fault (20/21/23) can never
 * be raised while hgatp.MODE=Bare.
 * cause_is_guest_page_fault() from common/cause_defs.h. */
#define g14_cause_not_guest_fault(c)  (!cause_is_guest_page_fault(c))

/* The .vm_test_region is NOLOAD, so test_exec_page content is
 * indeterminate. Plant a 32-bit `jr ra` (0x00008067) at its start so
 * a successful VS-mode fetch lands there and returns via the ra that
 * test_vs_exec_expect_fault pre-loads with the recovery label. */
#define G14_JR_RA_INST  0x00008067UL

static void g14_plant_exec_page(void)
{
    *(volatile uint32_t *)test_exec_page = (uint32_t)G14_JR_RA_INST;
}

/* ===================================================================
 * GBARE-01: VS-mode fetch pass-through under dual Bare.
 * The trivial translation applies no protection, so executing code at
 * a plain physical address must succeed without any trap.
 * =================================================================== */
TEST_REGISTER(test_gbare_01_vs_fetch);
bool test_gbare_01_vs_fetch(void) {
    TEST_BEGIN("GBARE-01: VS-mode fetch pass-through (dual Bare)");

    two_stage_ctx_t ctx;
    two_stage_init(&ctx, G14_BARE_VS, G14_BARE_G);

    g14_plant_exec_page();
    uintptr_t target = (uintptr_t)test_exec_page;

    /* Arm traps so an unexpected fault is recorded instead of fatal;
     * the helper returns the captured cause (0 == no fault). */
    trap_expect_begin();
    uintptr_t cause = two_stage_run_in_vs(&ctx, test_vs_exec_expect_fault,
                                          target);
    TEST_ASSERT("no trap on fetch", !trap_was_triggered());
    TEST_ASSERT_EQ("fetch executes (cause == 0)", cause, 0UL);
    trap_expect_end();

    two_stage_cleanup(&ctx);
    hyp_reset_state();
    HYP_TEST_END();
}

/* ===================================================================
 * GBARE-02: VU-mode load/store pass-through under dual Bare.
 * =================================================================== */
TEST_REGISTER(test_gbare_02_vu_load_store);
bool test_gbare_02_vu_load_store(void) {
    TEST_BEGIN("GBARE-02: VU-mode load/store pass-through (dual Bare)");

    two_stage_ctx_t ctx;
    two_stage_init(&ctx, G14_BARE_VS, G14_BARE_G);

    uintptr_t target = (uintptr_t)test_data_area;
    *(volatile uint64_t *)target = 0;

    uintptr_t r = two_stage_run_in_vu(&ctx, test_vs_read_write, target);
    TEST_ASSERT_EQ("VU-mode r/w succeeds with GPA == SPA", r, 0UL);

    two_stage_cleanup(&ctx);
    hyp_reset_state();
    HYP_TEST_END();
}

/* ===================================================================
 * GBARE-03: multi-address GPA == SPA strict equivalence.
 * Three distinct physical regions (code / data / test region) must
 * all be reachable at their exact physical addresses, proving the
 * address passes through "without modification".
 * =================================================================== */
TEST_REGISTER(test_gbare_03_multi_region);
bool test_gbare_03_multi_region(void) {
    TEST_BEGIN("GBARE-03: multi-address GPA==SPA equivalence (dual Bare)");

    two_stage_ctx_t ctx;
    two_stage_init(&ctx, G14_BARE_VS, G14_BARE_G);

    /* Region 1: code area -- compare against the M-mode read.
     * NOTE: function symbols may be only 2-byte aligned when RVC is
     * enabled, and some simulators (Spike) fault misaligned 8-byte
     * accesses, so align the probe address down to 8 bytes (still
     * inside .text). */
    uintptr_t code_addr = (uintptr_t)test_gbare_01_vs_fetch & ~0x7UL;
    uint64_t expect_code = *(volatile uint64_t *)code_addr;
    uintptr_t got = two_stage_run_in_vs(&ctx, test_vs_load, code_addr);
    TEST_ASSERT_EQ("code region passes through (GPA==SPA)",
                   got, (uintptr_t)expect_code);

    /* Region 2: data area -- plant a magic, read it back in VS-mode. */
    uintptr_t data_addr = (uintptr_t)test_data_area;
    *(volatile uint64_t *)data_addr = 0x1122334455667788ULL;
    got = two_stage_run_in_vs(&ctx, test_vs_load, data_addr);
    TEST_ASSERT_EQ("data region passes through (GPA==SPA)",
                   got, (uintptr_t)0x1122334455667788ULL);

    /* Region 3: test region -- plant another magic. */
    uintptr_t region_addr = TEST_REGION_BASE;
    *(volatile uint64_t *)region_addr = 0x99AABBCCDDEEFF00ULL;
    got = two_stage_run_in_vs(&ctx, test_vs_load, region_addr);
    TEST_ASSERT_EQ("test region passes through (GPA==SPA)",
                   got, (uintptr_t)0x99AABBCCDDEEFF00ULL);

    two_stage_cleanup(&ctx);
    hyp_reset_state();
    HYP_TEST_END();
}

/* ===================================================================
 * GBARE-04: PMP is the only remaining protection under Bare.
 * A PMP denial must surface as an access fault (1/5/7) -- never as a
 * guest-page-fault (20/21/23), which is unreachable with hgatp=Bare.
 * =================================================================== */
TEST_REGISTER(test_gbare_04_pmp_access_fault);
bool test_gbare_04_pmp_access_fault(void) {
    TEST_BEGIN("GBARE-04: PMP deny under Bare -> access fault, never guest fault");

    two_stage_ctx_t ctx;
    two_stage_init(&ctx, G14_BARE_VS, G14_BARE_G);

    uintptr_t data_target = (uintptr_t)test_data_area;
    uintptr_t exec_target = (uintptr_t)test_exec_page;
    g14_pmp_save_t save;

    /* --- load: deny the data page -> cause 5 --- */
    g14_pmp_deny_page(data_target, &save);
    trap_expect_begin();
    two_stage_run_in_vs(&ctx, test_vs_load_expect_fault, data_target);
    TEST_ASSERT("load trap triggered", trap_was_triggered());
    TEST_ASSERT_EQ("load access fault (cause=5)",
                   trap_get_cause(), (uintptr_t)CAUSE_LOAD_ACCESS_FAULT);
    TEST_ASSERT("load cause is not guest-page-fault",
                g14_cause_not_guest_fault(trap_get_cause()));
    trap_expect_end();
    g14_pmp_restore(&save);

    /* --- store: deny the data page -> cause 7 --- */
    g14_pmp_deny_page(data_target, &save);
    trap_expect_begin();
    two_stage_run_in_vs(&ctx, test_vs_store_expect_fault, data_target);
    TEST_ASSERT("store trap triggered", trap_was_triggered());
    TEST_ASSERT_EQ("store access fault (cause=7)",
                   trap_get_cause(), (uintptr_t)CAUSE_STORE_ACCESS_FAULT);
    TEST_ASSERT("store cause is not guest-page-fault",
                g14_cause_not_guest_fault(trap_get_cause()));
    trap_expect_end();
    g14_pmp_restore(&save);

    /* --- fetch: deny the exec page (X=0) -> cause 1 --- */
    g14_plant_exec_page();
    g14_pmp_deny_page(exec_target, &save);
    trap_expect_begin();
    uintptr_t cause = two_stage_run_in_vs(&ctx, test_vs_exec_expect_fault,
                                          exec_target);
    TEST_ASSERT("fetch trap triggered", trap_was_triggered());
    TEST_ASSERT_EQ("instruction access fault (cause=1)",
                   trap_get_cause(), (uintptr_t)CAUSE_INST_ACCESS_FAULT);
    TEST_ASSERT_EQ("fetch helper observed cause=1",
                   cause, (uintptr_t)CAUSE_INST_ACCESS_FAULT);
    TEST_ASSERT("fetch cause is not guest-page-fault",
                g14_cause_not_guest_fault(trap_get_cause()));
    trap_expect_end();
    g14_pmp_restore(&save);

    two_stage_cleanup(&ctx);
    hyp_reset_state();
    HYP_TEST_END();
}

/* ===================================================================
 * GBARE-05: trap reporting under Bare.
 * For a PMP access fault (not a guest-page-fault), norm:htval_trapval
 * requires htval == 0. For GVA, the note under norm:hstatus_gva_op
 * states that memory access traps writing a nonzero stval set GVA the
 * same as SPV; with V=1 (SPV=1) the faulting address IS a guest
 * virtual address, so GVA must be 1 even under dual Bare.
 *
 * hstatus.GVA/SPV are written only when the trap is taken into HS-mode.
 * The T-SBI delegation baseline (tsbi_deleg_hedeleg_baseline) delegates
 * load-access-fault (cause 5) down to VS, where those HS fields are never
 * written. Route cause 5 back to HS-mode so the fault is delivered there
 * and the framework captures hstatus.GVA/SPV; hyp_reset_state() in
 * HYP_TEST_END restores the baseline afterwards. */
TEST_REGISTER(test_gbare_05_trap_report);
bool test_gbare_05_trap_report(void) {
    TEST_BEGIN("GBARE-05: htval==0 and GVA==SPV on PMP fault under Bare");

    two_stage_ctx_t ctx;
    two_stage_init(&ctx, G14_BARE_VS, G14_BARE_G);

    uintptr_t data_target = (uintptr_t)test_data_area;
    g14_pmp_save_t save;
    g14_pmp_deny_page(data_target, &save);

    /* Deliver the load access fault into HS-mode so hstatus.GVA/SPV are
     * written and observable (see the block comment above). */
    setup_deleg_to_hs((uintptr_t)1UL << CAUSE_LOAD_ACCESS_FAULT);

    trap_expect_begin();
    two_stage_run_in_vs(&ctx, test_vs_load_expect_fault, data_target);
    TEST_ASSERT("trap triggered", trap_was_triggered());
    TEST_ASSERT_EQ("load access fault (cause=5)",
                   trap_get_cause(), (uintptr_t)CAUSE_LOAD_ACCESS_FAULT);
    CHECK_HTVAL("htval == 0 for non-guest-page-fault", 0);
    CHECK_GVA("hstatus.GVA == SPV == 1 (V=1 memory access trap)", 1);
    trap_expect_end();

    g14_pmp_restore(&save);
    two_stage_cleanup(&ctx);
    hyp_reset_state();
    HYP_TEST_END();
}
