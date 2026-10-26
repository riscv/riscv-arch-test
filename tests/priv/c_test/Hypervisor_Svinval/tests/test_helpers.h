/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_helpers.h - Common helpers for Hypervisor × Svinval cross tests
 *
 * Provides H/Svinval extension detection, HINVAL instruction wrappers,
 * VS/VU-mode trampolines, and PTE inspection utilities.
 *
 * Design: All test files are #included into test_register.c, so static
 * functions and variables are visible across all tests within the same
 * compilation unit.
 */

#ifndef HYPERVISOR_SVINVAL_TEST_HELPERS_H
#define HYPERVISOR_SVINVAL_TEST_HELPERS_H

#include "test_framework.h"
#include "vm/vm.h"
#include "test_utils.h"
#include "hyp/hyp_defs.h"
#include "hyp/hyp_csr.h"
#include "hyp/hyp_priv.h"
#include "hyp/hyp_reset.h"
#include "hyp/hyp_test.h"
#include "hyp/hyp_fence.h"
#include "hyp/hyp_ldst.h"
#include "hyp/gstage_pt.h"
#include "hyp/two_stage.h"
#include "hyp/two_stage_helpers.h"
#include "hyp/test_vs_helpers.h"
#include "hyp/hyp_trap.h"
#include "hyp/hyp_vs_trap.h"
#include "hyp_svinval_insn.h"

/* ===================================================================
 * Linker-provided test-region symbols (see Hypervisor_Svinval/kernel.ld).
 * =================================================================== */
extern uint8_t test_data_area[];
extern uint8_t test_fault_page[];
extern uint8_t test_exec_page[];
extern uint8_t test_exec_target[];
extern uint8_t __vm_test_region_start[];
extern uint8_t __vm_test_region_end[];

/* ===================================================================
 * Exception cause codes (from RISC-V Privileged Spec)
 *
 * Note: When hedeleg=0, VS-mode exceptions are routed to M-mode,
 * which uses S-mode cause codes (13/15) rather than VS-mode codes (5/7).
 * This test suite sets hedeleg=0 in hyp_reset.c, so we expect:
 *   - VS-mode load page fault = 13 (S-mode encoding)
 *   - VS-mode store/AMO page fault = 15 (S-mode encoding)
 * =================================================================== */
#define CAUSE_VS_STORE_PAGE_FAULT      15  /* S-mode encoding when hedeleg=0 */


/* vs_pte_modify() / g_pte_modify() are provided by
 * common/hyp/two_stage_helpers.h. */

/* ===================================================================
 * VS-mode test trampolines for HINVAL instructions
 * =================================================================== */

/* VS-mode: execute HINVAL.VVMA(arg, 0) */
static uintptr_t vs_exec_hinval_vvma(uintptr_t arg) {
    trap_expect_begin();
    HINVAL_VVMA(arg, 0);
    trap_expect_end();
    if (trap_was_triggered())
        return trap_get_cause();
    return 0;
}

/* VS-mode: execute HINVAL.GVMA(arg, 0) */
static uintptr_t vs_exec_hinval_gvma(uintptr_t arg) {
    trap_expect_begin();
    HINVAL_GVMA(arg, 0);
    trap_expect_end();
    if (trap_was_triggered())
        return trap_get_cause();
    return 0;
}

/* VS-mode: execute SFENCE.W.INVAL */
static uintptr_t vs_exec_sfence_w_inval(uintptr_t arg) {
    (void)arg;
    trap_expect_begin();
    SFENCE_W_INVAL();
    trap_expect_end();
    if (trap_was_triggered())
        return trap_get_cause();
    return 0;
}

/* VS-mode: execute SFENCE.INVAL.IR */
static uintptr_t vs_exec_sfence_inval_ir(uintptr_t arg) {
    (void)arg;
    trap_expect_begin();
    SFENCE_INVAL_IR();
    trap_expect_end();
    if (trap_was_triggered())
        return trap_get_cause();
    return 0;
}

/* ===================================================================
 * VU-mode test trampolines for HINVAL instructions
 * =================================================================== */

/* VU-mode: execute HINVAL.VVMA(arg, 0) */
static uintptr_t vu_exec_hinval_vvma(uintptr_t arg) {
    trap_expect_begin();
    HINVAL_VVMA(arg, 0);
    trap_expect_end();
    if (trap_was_triggered())
        return trap_get_cause();
    return 0;
}

/* VU-mode: execute HINVAL.GVMA(arg, 0) */
static uintptr_t vu_exec_hinval_gvma(uintptr_t arg) {
    trap_expect_begin();
    HINVAL_GVMA(arg, 0);
    trap_expect_end();
    if (trap_was_triggered())
        return trap_get_cause();
    return 0;
}

/* VU-mode: execute SFENCE.W.INVAL */
static uintptr_t vu_exec_sfence_w_inval(uintptr_t arg) {
    (void)arg;
    trap_expect_begin();
    SFENCE_W_INVAL();
    trap_expect_end();
    if (trap_was_triggered())
        return trap_get_cause();
    return 0;
}

/* VU-mode: execute SFENCE.INVAL.IR */
static uintptr_t vu_exec_sfence_inval_ir(uintptr_t arg) {
    (void)arg;
    trap_expect_begin();
    SFENCE_INVAL_IR();
    trap_expect_end();
    if (trap_was_triggered())
        return trap_get_cause();
    return 0;
}

/* VU-mode: execute SINVAL.VMA(arg, 0) */
static uintptr_t vu_exec_sinval_vma(uintptr_t arg) {
    trap_expect_begin();
    SINVAL_VMA(arg, 0);
    trap_expect_end();
    if (trap_was_triggered())
        return trap_get_cause();
    return 0;
}

/* ===================================================================
 * VS-mode memory access trampolines
 * =================================================================== */

/* vs_store is provided by common/test_utils.h (probe_store), run in VS-mode. */

#endif /* HYPERVISOR_SVINVAL_TEST_HELPERS_H */
