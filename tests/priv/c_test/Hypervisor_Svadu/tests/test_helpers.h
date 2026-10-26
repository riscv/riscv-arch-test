/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_helpers.h - Common helpers for Hypervisor × Svadu cross tests
 *
 * Provides H/Svadu extension detection, henvcfg/menvcfg ADUE access,
 * PTE inspection utilities, and VS-mode test trampolines.
 *
 * Design: All test files are #included into test_register.c, so static
 * functions and variables are visible across all tests within the same
 * compilation unit.
 */

#ifndef HYPERVISOR_SVADU_TEST_HELPERS_H
#define HYPERVISOR_SVADU_TEST_HELPERS_H

#include "test_framework.h"
#include "vm/vm.h"
#include "test_utils.h"
#include "hyp/hyp_defs.h"
#include "hyp/hyp_csr.h"
#include "hyp/hyp_priv.h"
#include "hyp/hyp_reset.h"
#include "hyp/hyp_test.h"
#include "hyp/hyp_ldst.h"
#include "hyp/hyp_fence.h"
#include "hyp/gstage_pt.h"
#include "hyp/two_stage.h"
#include "hyp/two_stage_helpers.h"
#include "hyp/test_vs_helpers.h"
#include "hyp/hyp_trap.h"
#include "hyp/hyp_vs_trap.h"

/* ===================================================================
 * Linker-provided test-region symbols (see Hypervisor_Svadu/kernel.ld).
 * =================================================================== */
extern uint8_t test_data_area[];
extern uint8_t test_fault_page[];
extern uint8_t test_exec_page[];
extern uint8_t test_exec_target[];
extern uint8_t __vm_test_region_start[];
extern uint8_t __vm_test_region_end[];

/* ===================================================================
 * Svadu availability
 *
 * Svadu support is config-declaration driven: gate on the compile-time
 * SVADU_AVAILABLE macro (normalized in common/capabilities.h from
 * SVADU_SUPPORTED in rvtest_config.h). Do NOT probe menvcfg.ADUE
 * writability at runtime.
 * =================================================================== */

/* ===================================================================
 * henvcfg.ADUE access helpers
 *
 * For setting ADUE, call henvcfg_set_adue() from common/hyp/hyp_csr.h
 * directly.
 * =================================================================== */
static inline int henvcfg_adue_read(void) {
    /* henvcfg.ADUE is bit 61, same as menvcfg.ADUE */
    return (henvcfg_read() & MENVCFG_ADUE) ? 1 : 0;
}

/* ===================================================================
 * menvcfg.ADUE access helpers
 * =================================================================== */
static inline void menvcfg_adue_set(int enable) {
    uintptr_t val = tsbi_csr_read(CSR_MENVCFG);
    if (enable)
        val |= MENVCFG_ADUE;
    else
        val &= ~MENVCFG_ADUE;
    tsbi_csr_write(CSR_MENVCFG, val);
}

static inline int menvcfg_adue_read(void) {
    return (tsbi_csr_read(CSR_MENVCFG) & MENVCFG_ADUE) ? 1 : 0;
}

/* ===================================================================
 * PTE inspection / modification helpers
 * =================================================================== */

/* Read VS-stage PTE at the given VA and level */
static uintptr_t vs_pte_read(two_stage_ctx_t *ctx, uintptr_t va, int level) {
    uintptr_t *pte = pt_get_pte(&ctx->vs_ctx, va, level);
    return pte ? *pte : 0;
}

/* Clear A/D bits in VS-stage PTE */
static void vs_pte_clear_ad(two_stage_ctx_t *ctx, uintptr_t va, int level) {
    uintptr_t *pte = pt_get_pte(&ctx->vs_ctx, va, level);
    if (pte) {
        *pte &= ~(PTE_A | PTE_D);
        hfence_vvma_all();
    }
}

/* Clear A/D bits in VS-stage PTE WITHOUT flushing TLB.
 * Used when the caller needs to preserve cached TLB entries
 * (e.g., cross-VMID ADUE synchronization tests where flushing
 * would destroy TLB state for other VMIDs). */
static void vs_pte_clear_ad_nofence(two_stage_ctx_t *ctx, uintptr_t va, int level) {
    uintptr_t *pte = pt_get_pte(&ctx->vs_ctx, va, level);
    if (pte) {
        *pte &= ~(PTE_A | PTE_D);
    }
}

/* ===================================================================
 * VS-mode test trampolines
 * =================================================================== */

/* vs_load is provided by common/test_utils.h (probe_load), run in VS-mode. */

#endif /* HYPERVISOR_SVADU_TEST_HELPERS_H */
