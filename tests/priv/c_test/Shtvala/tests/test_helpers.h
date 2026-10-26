/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef SHTVALA_TEST_HELPERS_H
#define SHTVALA_TEST_HELPERS_H

/* ===================================================================
 * Shared declarations for shtvala tests (each test_*.c is
 * pulled in by test_register.c).
 *
 * Shtvala (Trap Value Reporting for H-extension, v1.0) only mandates:
 *   norm:H_htval — on guest-page-fault, htval := faulting GPA >> 2.
 *
 * Test plan layout (see DOCS/testplan/shtvala_test_plan.md):
 *   Group 1 HTVAL-REG        : htval CSR existence / WARL probe
 *   Group 2 HTVAL-LGP/SGP/IGP: explicit G-stage GPF (load/store/fetch)
 *   Group 3 HTVAL-IMP        : implicit VS-stage PTE GPF
 *   Group 4 HTVAL-STR        : straddle / misaligned across pages
 *   Group 5 HTVAL-HLV        : HLV/HLVX/HSV from M-mode hitting G-stage
 *   Group 6 HTVAL-MOD        : Sv39x4/48x4/57x4 mode coverage
 *   Group 7 HTVAL-CLR        : non-GPF traps must NOT clobber htval
 *   Group 8 HTVAL-CON        : htval/stval consistency (low-bit reconstruction)
 *   Group 9 HTVAL-GVA        : hstatus.GVA linkage
 *
 * Group 3 uses VS-stage page tables (vsatp=Sv39) + G-stage to test
 * implicit PTE walk faults.
 * Group 5 uses HLV/HLVX/HSV from M-mode (hyp_ldst.h), which work
 * when hgatp != BARE regardless of vsatp.
 * =================================================================== */

#include "test_framework.h"
#include "vm/vm.h"
#include "hyp/hyp_defs.h"
#include "hyp/hyp_csr.h"
#include "hyp/hyp_priv.h"
#include "hyp/hyp_reset.h"
#include "hyp/hyp_test.h"
#include "hyp/hyp_ldst.h"
#include "hyp/gstage_pt.h"
#include "hyp/two_stage.h"
#include "hyp/test_vs_helpers.h"
#include "hyp/hyp_test_helpers.h"    /* setup_gstage_with_victim, fire_vs_*_fault */
#include "hyp/two_stage_helpers.h"   /* ts2_setup_with_g_victim, ts2_run_check_fault */

/* Linker-provided test-region symbols (see shtvala/kernel.ld). */
extern uint8_t test_data_area[];
extern uint8_t test_fault_page[];
extern uint8_t test_exec_page[];
extern uint8_t test_exec_target[];
extern uint8_t __vm_test_region_start[];
extern uint8_t __vm_test_region_end[];

/* ===================================================================
 * Shared helpers (defined in test_helpers.c).
 * =================================================================== */

/* Build a G-stage with a chosen hgatp mode that:
 *   1. identity-maps low-mem (kernel + UART) at 2MB,
 *   2. identity-maps the .vm_test_region pages at 4KB,
 *   3. installs the caller-supplied flags as the leaf for the 4KB
 *      page that contains victim_gpa.
 * Does NOT activate hgatp (does not call gpt_enable).
 * (For the fixed SUITE_HGATP_MODE case, call setup_gstage_with_victim()
 * from common/hyp/hyp_test_helpers.h directly.)
 */
void _setup_with_victim_mode(two_stage_ctx_t *ctx,
                             uintptr_t victim_gpa,
                             uintptr_t victim_flags,
                             int g_mode);

/* Run helper(target) inside VS-mode under a G-stage built with the
 * supplied victim flags. Returns true iff a guest-page-fault fires
 * with cause == expected_cause. Calls hyp_reset_state() on exit. */
bool _vsfault_check(uintptr_t (*helper)(uintptr_t),
                    uintptr_t target,
                    uintptr_t victim_flags,
                    uintptr_t expected_cause);

/* VS-mode fetch fault firer: sets up G-stage, runs helper in VS-mode,
 * does NOT call hyp_reset_state(); trap_record remains valid for
 * post-trap inspection. Caller must call hyp_reset_state() when done.
 * Returns true iff the trap actually fired.
 * (For load/store faults, call fire_vs_load_fault()/fire_vs_store_fault()
 * from common/hyp/hyp_test_helpers.h directly.) */
bool _fire_fetch_fault(uintptr_t victim_gpa, uintptr_t flags);

/* Mode-aware VS-mode load fault firer. */
bool _fire_load_fault_mode(uintptr_t victim_gpa, uintptr_t flags, int g_mode);

/* ===================================================================
 * Group 5 HLV/HLVX/HSV fault firers (M-mode, G-stage active).
 *
 * HLV/HLVX/HSV are valid in M-mode and HS-mode. They always go
 * through two-stage address translation: vsatp (VS-stage) + hgatp
 * (G-stage). With vsatp=BARE the address is treated as a GPA and
 * only hgatp is consulted. A failing G-stage lookup raises a
 * guest-page-fault that is captured by the M-mode trap handler
 * (mtval2 -> trap_record.htval, as for all other GPF tests).
 *
 * These firers:
 *   1. Set up G-stage page tables (victim page has flags=0, V=0).
 *   2. Enable G-stage (hgatp = Sv39x4) without entering VS-mode.
 *   3. Execute the instruction inside EXPECT_GUEST_PAGE_FAULT.
 *   4. Disable G-stage.
 *   5. Leave trap_record alive; caller must call hyp_reset_state().
 *   Returns true iff the expected guest-page-fault fired.
 * =================================================================== */
bool _fire_hlvx_fault_priv(uintptr_t victim_gpa, uintptr_t flags,
                           unsigned eff_priv);    /* → cause=21 */
bool _fire_hlvx_fault(uintptr_t victim_gpa, uintptr_t flags);  /* → cause=21, eff=VU */
bool _fire_hlvx_fault_bare(uintptr_t victim_gpa, uintptr_t flags); /* → cause=21, vsatp=BARE */
bool _fire_hlv_fault (uintptr_t victim_gpa, uintptr_t flags);  /* → cause=21 */
bool _fire_hsv_fault (uintptr_t victim_gpa, uintptr_t flags);  /* → cause=23 */

/* AMO fault firer: set up G-stage, run AMO in VS-mode.
 * Does NOT call hyp_reset_state(); caller must do it. */
bool _fire_amo_fault(uintptr_t victim_gpa, uintptr_t flags);

/* Two-stage (vsatp=Sv39 + G-stage) explicit load fault firer.
 * Maps test_gva -> test_gpa in VS-stage, makes test_gpa invalid in G-stage.
 * Returns true iff GPF fired. Caller must call hyp_reset_state(). */
bool _fire_two_stage_load_fault(uintptr_t test_gva, uintptr_t test_gpa,
                                uintptr_t victim_flags);

/* ===================================================================
 * Group 3 implicit PTE fault helper (VS-stage + G-stage).
 *
 * For the fixed SUITE_HGATP_MODE case, call
 * setup_implicit_walk_victim_level() from common/hyp/hyp_test_helpers.h
 * directly. _setup_imp_victim_mode is the mode-parameterized variant
 * for testing under different G-stage modes (e.g. Sv48x4 for
 * HTVAL-IMP-07); it builds a two-stage context:
 *   VS-stage (Sv39):  identity maps kernel at 2MB + test_va at 4KB
 *   G-stage (Sv39x4): identity maps kernel + page tables at 4KB and
 *     test region at 4KB, EXCEPT the VS-stage page table page at
 *     @victim_pt_level, which gets @victim_g_flags.
 *
 * Returns: GPA of the victim page table page (for htval computation).
 *          Caller must call two_stage_cleanup + hyp_reset_state.
 * =================================================================== */
uintptr_t _setup_imp_victim_mode(two_stage_ctx_t *ctx,
                                 uintptr_t test_va,
                                 int victim_pt_level,
                                 uintptr_t victim_g_flags,
                                 int vs_mode, int g_mode);

#endif /* SHTVALA_TEST_HELPERS_H */
