/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * test_helpers.c - Shared helpers for shtvala G-stage tests
 *
 * Mirrors sv39x4/tests/test_helpers.c with additions:
 *   - mode-parameterized setup/firer for Group 6 (HTVAL-MOD).
 *   - dedicated _fire_fetch_fault, used by
 *     Groups 2/8/9 to inspect post-trap CSRs (trap_record kept
 *     alive — caller must call hyp_reset_state() afterwards).
 *     (Load/store GPF firers use common fire_vs_load_fault /
 *     fire_vs_store_fault directly.)
 *   - _fire_hlvx_fault / _fire_hlv_fault / _fire_hsv_fault for
 *     Group 5: execute HLV/HLVX/HSV from M-mode while two-stage
 *     translation is active, triggering a G-stage fault.
 *     HLVX uses vsatp=Sv39 (identity-mapped) for correct cause
 *     routing; HLV/HSV use vsatp=BARE.
 *
 * See shtvala/tests/test_helpers.h for prototypes / contracts.
 * =================================================================== */

#include "test_helpers.h"

void _setup_with_victim_mode(two_stage_ctx_t *ctx,
                             uintptr_t victim_gpa,
                             uintptr_t victim_flags,
                             int g_mode)
{
    ts2_setup_with_g_victim(ctx, SATP_MODE_BARE, g_mode,
                            victim_gpa, victim_flags);
}

bool _vsfault_check(uintptr_t (*helper)(uintptr_t),
                    uintptr_t target,
                    uintptr_t victim_flags,
                    uintptr_t expected_cause)
{
    two_stage_ctx_t ctx;
    setup_gstage_with_victim(&ctx, target, victim_flags);
    return ts2_run_check_fault(&ctx, helper, target, expected_cause);
}

/* ---- VS-mode inline fault firers (do NOT reset hyp state) --------- */

bool _fire_load_fault_mode(uintptr_t victim_gpa, uintptr_t flags, int g_mode) {
    two_stage_ctx_t ctx;
    ts2_setup_with_g_victim(&ctx, SATP_MODE_BARE, g_mode, victim_gpa, flags);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_load_expect_fault, victim_gpa);
    bool fired = trap_was_triggered();
    trap_expect_end();

    two_stage_cleanup(&ctx);
    return fired;
}

bool _fire_fetch_fault(uintptr_t victim_gpa, uintptr_t flags) {
    two_stage_ctx_t ctx;
    setup_gstage_with_victim(&ctx, victim_gpa, flags);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_exec_expect_fault, victim_gpa);
    bool fired = trap_was_triggered();
    trap_expect_end();

    two_stage_cleanup(&ctx);
    return fired;
}

/* ---- AMO fault firer (VS-mode, G-stage active) -------------------- */

static uintptr_t vs_amo_expect_fault(uintptr_t addr) {
    uintptr_t tmp;
    asm volatile ("amoadd.d %0, %1, (%2)"
                  : "=r"(tmp) : "r"(1UL), "r"(addr) : "memory");
    return 0;
}

bool _fire_amo_fault(uintptr_t victim_gpa, uintptr_t flags) {
    two_stage_ctx_t ctx;
    setup_gstage_with_victim(&ctx, victim_gpa, flags);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, vs_amo_expect_fault, victim_gpa);
    bool fired = trap_was_triggered();
    trap_expect_end();

    two_stage_cleanup(&ctx);
    return fired;
}

/* ---- Two-stage (vsatp=Sv39 + G-stage) explicit load fault firer --- */

bool _fire_two_stage_load_fault(uintptr_t test_gva, uintptr_t test_gpa,
                                uintptr_t victim_flags)
{
    two_stage_ctx_t ctx;
    gpt_pool_reset();
    two_stage_init(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    /* VS-stage: identity-map kernel at 2MB. */
    uintptr_t lo_base = PLATFORM_MEM_BASE & ~(PAGE_SIZE_2M - 1);
    uintptr_t r_start = (uintptr_t)__vm_test_region_start;
    uintptr_t lo_end  = r_start & ~(PAGE_SIZE_2M - 1);
    uintptr_t vs_flags = PTE_V | PTE_R | PTE_W | PTE_X | PTE_A | PTE_D;

    two_stage_vs_identity(&ctx, lo_base, lo_end - lo_base,
                          vs_flags, PT_LEVEL_2M);

    /* VS-stage: map test_gva -> test_gpa at 4KB with full perms. */
    two_stage_vs_map(&ctx, test_gva, test_gpa, vs_flags, PT_LEVEL_4K);

    /* G-stage: identity-map kernel at 2MB. */
    two_stage_setup_identity(&ctx, lo_base, lo_end - lo_base,
                             G_FLAGS_RWXU_AD, PT_LEVEL_2M);

    /* G-stage: identity-map test region at 4KB (for VS PT pages). */
    uintptr_t r_end = (uintptr_t)__vm_test_region_end;
    two_stage_setup_identity(&ctx, r_start, r_end - r_start,
                             G_FLAGS_RWXU_AD, PT_LEVEL_4K);

    /* Override victim page (test_gpa) with supplied flags. */
    uintptr_t victim_page = test_gpa & ~(PAGE_SIZE_4K - 1);
    two_stage_g_map_page(&ctx, victim_page, victim_page,
                         victim_flags, PT_LEVEL_4K);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_load_expect_fault, test_gva);
    bool fired = trap_was_triggered();
    trap_expect_end();

    two_stage_cleanup(&ctx);
    return fired;
}

/* ---- Group 3 implicit PTE fault helper (VS-stage + G-stage) ------- */

uintptr_t _setup_imp_victim_mode(two_stage_ctx_t *ctx,
                                 uintptr_t test_va,
                                 int victim_pt_level,
                                 uintptr_t victim_g_flags,
                                 int vs_mode, int g_mode)
{
    /* pt_pool_reset() is called inside two_stage_init for non-BARE. */
    gpt_pool_reset();
    two_stage_init(ctx, vs_mode, g_mode);

    /* --- VS-stage (UART/CLINT auto-mapped by framework) --- */
    uintptr_t lo_base  = PLATFORM_MEM_BASE & ~(PAGE_SIZE_2M - 1);
    uintptr_t r_start  = (uintptr_t)__vm_test_region_start;
    uintptr_t lo_end   = r_start & ~(PAGE_SIZE_2M - 1);
    uintptr_t vs_flags = PTE_V | PTE_R | PTE_W | PTE_X | PTE_A | PTE_D;

    two_stage_vs_identity(ctx, lo_base, lo_end - lo_base,
                          vs_flags, PT_LEVEL_2M);

    /* test_va -> test region GPA (non-identity: separate VPN[2]). */
    two_stage_vs_map(ctx, test_va, r_start, vs_flags, PT_LEVEL_4K);

    /* Query the victim PT-page GPA. */
    uintptr_t victim_gpa =
        two_stage_vs_pt_page_addr(ctx, test_va, victim_pt_level);
    uintptr_t victim_page = victim_gpa & ~(PAGE_SIZE_4K - 1);

    /* --- G-stage: 4KB over kernel + page tables for fine-grained
     *     control; UART auto-mapped by framework. --- */
    two_stage_setup_identity(ctx, lo_base, r_start - lo_base,
                             G_FLAGS_RWXU_AD, PT_LEVEL_4K);

    uintptr_t r_end = (uintptr_t)__vm_test_region_end;
    two_stage_setup_identity(ctx, r_start, r_end - r_start,
                             G_FLAGS_RWXU_AD, PT_LEVEL_4K);

    /* Override victim PT page. */
    two_stage_g_map_page(ctx, victim_page, victim_page,
                         victim_g_flags, PT_LEVEL_4K);

    return victim_gpa;
}

/* ---- Group 5 HLV/HLVX/HSV M-mode fault firers --------------------- *
 *
 * Strategy: HLV/HLVX/HSV are legal in M-mode. With hgatp != BARE,
 * the virtual address goes through two-stage translation. A failing
 * G-stage lookup triggers a guest-page-fault whose cause depends on
 * the instruction type (per hypervisor.adoc:1505-1507, HLVX raises
 * the same exceptions as other LOAD instructions):
 *   HLVX  -> CAUSE_LOAD_GUEST_PAGE_FAULT  (cause=21)
 *   HLV   -> CAUSE_LOAD_GUEST_PAGE_FAULT  (cause=21)
 *   HSV   -> CAUSE_STORE_GUEST_PAGE_FAULT (cause=23)
 * The M-mode trap handler captures mtval2 (= GPA>>2) into the trap
 * record, so trap_get_htval() works the same as for VS-mode tests.
 *
 * Normal M-mode loads/stores are NOT subject to G-stage translation,
 * so enabling hgatp here only affects the HLV/HLVX/HSV instruction
 * itself. The caller must call hyp_reset_state() after inspecting
 * the trap record.
 *
 * Effective privilege of HLV/HLVX/HSV is controlled by hstatus.SPVP:
 *   SPVP=0 -> VU-mode access  (PTE.U must be 1 to pass VS-stage)
 *   SPVP=1 -> VS-mode access  (PTE.U must be 0, unless vsstatus.SUM=1)
 * The VS-stage page-table permissions MUST match the chosen SPVP, or
 * VS-stage will raise a page fault before G-stage is consulted.
 *
 * HLVX implementation note: vsatp=Sv39 is used (not BARE) so any
 * G-stage failure produces a deterministic CAUSE_LOAD_GUEST_PAGE_FAULT
 * (cause=21) with VS-stage translation explicitly succeeding first.
 * HLV/HSV use vsatp=BARE since their cause classification is
 * unambiguous regardless of vsatp mode.
 * ------------------------------------------------------------------- */

bool _fire_hlvx_fault_priv(uintptr_t victim_gpa, uintptr_t flags,
                           unsigned eff_priv) {
    two_stage_ctx_t ctx;

    /* HLVX needs vsatp=Sv39 (not BARE) for unambiguous cause routing. */
    gpt_pool_reset();
    two_stage_init(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    /* VS-stage PTE.U bit must agree with effective privilege:
     *   PRIV_U (VU) -> set PTE.U=1
     *   PRIV_S (VS) -> clear PTE.U  (avoid SUM dependency) */
    uintptr_t vs_flags = PTE_V | PTE_R | PTE_W | PTE_X | PTE_A | PTE_D;
    if (eff_priv == PRIV_U) vs_flags |= PTE_U;

    /* VS-stage: identity-map so HLVX address translates VA=GPA. */
    uintptr_t lo_base  = PLATFORM_MEM_BASE & ~(PAGE_SIZE_2M - 1);
    uintptr_t lo_end   = (uintptr_t)__vm_test_region_start
                         & ~(PAGE_SIZE_2M - 1);
    two_stage_vs_identity(&ctx, lo_base, lo_end - lo_base,
                         vs_flags, PT_LEVEL_2M);
    uintptr_t r_start = (uintptr_t)__vm_test_region_start;
    uintptr_t r_size  = (uintptr_t)__vm_test_region_end - r_start;
    two_stage_vs_identity(&ctx, r_start, r_size, vs_flags, PT_LEVEL_4K);

    /* G-stage: identity-map with victim override. */
    two_stage_setup_identity(&ctx, lo_base, lo_end - lo_base,
                             G_FLAGS_RWXU_AD, PT_LEVEL_2M);
    two_stage_setup_identity(&ctx, r_start, r_size,
                             G_FLAGS_RWXU_AD, PT_LEVEL_4K);
    uintptr_t victim_page = victim_gpa & ~(PAGE_SIZE_4K - 1);
    two_stage_g_map_page(&ctx, victim_page, victim_page,
                         flags, PT_LEVEL_4K);

    /* Set effective privilege for HLV/HLVX/HSV via hstatus.SPVP.
     * hyp_reset_state() in the test epilogue will clear SPVP back to 0. */
    hstatus_set_spvp(eff_priv);

    /* Enable both stages without entering VS-mode. */
    two_stage_enable(&ctx, /*vmid=*/0);

    trap_expect_begin();
    (void)hlvx_wu(victim_gpa);  /* HLVX.WU: load-class exception per spec */
    bool fired = trap_was_triggered();
    trap_expect_end();

    two_stage_cleanup(&ctx);
    return fired;
}

/* Backward-compatible wrapper: defaults to VU effective privilege. */
bool _fire_hlvx_fault(uintptr_t victim_gpa, uintptr_t flags) {
    return _fire_hlvx_fault_priv(victim_gpa, flags, PRIV_U);
}

/* HLVX with vsatp=BARE: VA is treated directly as GPA.
 * No VS-stage translation, so SPVP/PTE.U are irrelevant.
 * This verifies HLVX cause classification without VS-stage involvement. */
bool _fire_hlvx_fault_bare(uintptr_t victim_gpa, uintptr_t flags) {
    two_stage_ctx_t ctx;
    _setup_with_victim_mode(&ctx, victim_gpa, flags, SUITE_HGATP_MODE);

    /* Enable G-stage (vsatp=BARE set inside _setup_with_victim_mode). */
    two_stage_enable(&ctx, /*vmid=*/0);

    trap_expect_begin();
    (void)hlvx_wu(victim_gpa);  /* HLVX.WU with vsatp=BARE */
    bool fired = trap_was_triggered();
    trap_expect_end();

    two_stage_cleanup(&ctx);
    return fired;
}

bool _fire_hlv_fault(uintptr_t victim_gpa, uintptr_t flags) {
    two_stage_ctx_t ctx;
    _setup_with_victim_mode(&ctx, victim_gpa, flags, SUITE_HGATP_MODE);

    two_stage_enable(&ctx, /*vmid=*/0);

    trap_expect_begin();
    (void)hlv_d(victim_gpa);    /* HLV.D: load semantics */
    bool fired = trap_was_triggered();
    trap_expect_end();

    two_stage_cleanup(&ctx);
    return fired;
}

bool _fire_hsv_fault(uintptr_t victim_gpa, uintptr_t flags) {
    two_stage_ctx_t ctx;
    _setup_with_victim_mode(&ctx, victim_gpa, flags, SUITE_HGATP_MODE);

    two_stage_enable(&ctx, /*vmid=*/0);

    trap_expect_begin();
    hsv_d(victim_gpa, 0);       /* HSV.D: store semantics */
    bool fired = trap_was_triggered();
    trap_expect_end();

    two_stage_cleanup(&ctx);
    return fired;
}
