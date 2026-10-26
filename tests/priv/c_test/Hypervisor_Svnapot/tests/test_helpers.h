/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_helpers.h - Common helpers for Hypervisor x Svnapot cross tests
 *
 * Provides H/Svnapot extension detection, NAPOT PTE construction and
 * installation functions for both G-stage and VS-stage, and VS-mode
 * test trampolines.
 *
 * Design: All test files are #included into test_register.c, so static
 * functions and variables are visible across all tests within the same
 * compilation unit.
 */

#ifndef HYPERVISOR_SVNAPOT_TEST_HELPERS_H
#define HYPERVISOR_SVNAPOT_TEST_HELPERS_H

#include "test_framework.h"
#include "vm/vm.h"
#include "hyp/hyp_defs.h"
#include "hyp/hyp_csr.h"
#include "hyp/hyp_priv.h"
#include "hyp/hyp_reset.h"
#include "hyp/hyp_test.h"
#include "hyp/hyp_fence.h"
#include "hyp/gstage_pt.h"
#include "hyp/two_stage.h"
#include "hyp/two_stage_helpers.h"
#include "hyp/test_vs_helpers.h"
#include "hyp/hyp_trap.h"
#include "hyp/hyp_vs_trap.h"

/* ===================================================================
 * Linker-provided test-region symbols (see kernel.ld).
 * =================================================================== */
extern uint8_t __vm_test_region_start[];
extern uint8_t __vm_test_region_end[];

/* First 64 KiB NAPOT region */
#define NAPOT_TEST_REGION_0  TEST_REGION_BASE

/* Second 64 KiB NAPOT region */
#define NAPOT_TEST_REGION_1  (TEST_REGION_BASE + NAPOT_64K_SIZE)

/* ===================================================================
 * NAPOT PTE Constants (from Svnapot spec)
 * =================================================================== */

/* NAPOT 64 KiB region parameters */
#define NAPOT_64K_PAGES     16                      /* 16 x 4 KiB pages */
#define NAPOT_64K_SIZE      (64 * 1024)             /* 64 KiB = 0x10000 */
#define NAPOT_64K_MASK      (NAPOT_64K_SIZE - 1)    /* 0xFFFF */
#define NAPOT_BITS_64K      4                       /* napot_bits = 4 */

/* ppn[0] encoding for 64 KiB NAPOT: low 4 bits = 1000 (0x8) */
#define NAPOT_64K_PPN0_ENC  0x8UL

/* PTE flags mask (bits 9:0, includes RSW) */
#define PTE_ALL_FLAGS_MASK  0x3FFUL

/* MAGIC_WRITE is provided by common/vm/vm_defs.h. */

/* ===================================================================
 * NAPOT PTE Construction Functions
 * =================================================================== */

/*
 * napot_make_pte - Construct a valid 64 KiB NAPOT PTE
 * @pa:    Physical address (must be 64 KiB aligned)
 * @flags: PTE flags (PTE_V | PTE_R | PTE_W | etc.)
 *
 * PTE layout:
 *   bit 63:     N = 1
 *   bits 53-10: PPN (with ppn[0][3:0] = 1000)
 *   bits 9-0:   flags (RSW + DAGUXWRV)
 */
static inline uintptr_t napot_make_pte(uintptr_t pa, uintptr_t flags) {
    uintptr_t ppn = pa >> PAGE_SHIFT;
    ppn = (ppn & ~0xFUL) | NAPOT_64K_PPN0_ENC;
    return PTE_N | (ppn << PTE_PPN_SHIFT) | (flags & PTE_ALL_FLAGS_MASK);
}

/*
 * napot_make_reserved_pte - Construct a NAPOT PTE with reserved encoding
 * @pa:        Physical address
 * @flags:     PTE flags
 * @ppn0_low4: Low 4 bits of ppn[0] (must be a reserved encoding, e.g. 0x1)
 */
static inline uintptr_t napot_make_reserved_pte(uintptr_t pa,
                                                 uintptr_t flags,
                                                 unsigned ppn0_low4) {
    uintptr_t ppn = pa >> PAGE_SHIFT;
    ppn = (ppn & ~0xFUL) | (ppn0_low4 & 0xFUL);
    return PTE_N | (ppn << PTE_PPN_SHIFT) | (flags & PTE_ALL_FLAGS_MASK);
}

/* ===================================================================
 * Svnapot availability
 *
 * Svnapot support is config-declaration driven: gate on the compile-time
 * SVNAPOT_AVAILABLE macro (normalized in common/capabilities.h from
 * SVNAPOT_SUPPORTED in rvtest_config.h). Do NOT probe misa.N or install
 * a NAPOT PTE at runtime -- QEMU's "max" CPU implements Svnapot while
 * leaving misa.N clear, so a runtime probe yields a false negative.
 * =================================================================== */

/* ===================================================================
 * G-stage NAPOT PTE Installation
 *
 * G-stage uses Sv39x4 format. Level-0 (4KB leaf) PTEs use the same
 * encoding as VS-stage. A 64 KiB NAPOT region spans 16 consecutive
 * level-0 PTE slots, all sharing the same PPN with N=1.
 * =================================================================== */

/*
 * gstage_napot_install_pte - Install a 64 KiB NAPOT PTE into G-stage
 * @g_ctx:   G-stage page table context
 * @gpa:     Guest physical address (must be 64 KiB aligned)
 * @pte_val: Pre-constructed NAPOT PTE value
 *
 * Creates the page table path via gpt_map_page(), then overwrites
 * all 16 consecutive L0 PTE slots covering the 64 KiB region.
 */
static void gstage_napot_install_pte(gpt_context_t *g_ctx,
                                      uintptr_t gpa,
                                      uintptr_t pte_val) {
    uintptr_t base_gpa = gpa & ~NAPOT_64K_MASK;

    /* Create the page table path for the base GPA at 4KB level */
    gpt_map_page(g_ctx, base_gpa, base_gpa,
                 PTE_V | PTE_R | PTE_U | PTE_A | PTE_D, PT_LEVEL_4K);

    /* Get pointer to the L0 PTE for the base GPA */
    uintptr_t *base_pte = gpt_get_pte(g_ctx, base_gpa, PT_LEVEL_4K);
    if (!base_pte) {
        LOG_E("gstage_napot_install_pte: could not get L0 PTE\n");
        return;
    }

    /* Overwrite all 16 consecutive L0 slots with the NAPOT PTE.
     * Since base_gpa is 64 KiB aligned, VPN[0] low 4 bits are 0,
     * so the 16 entries are contiguous in the L0 page table. */
    for (int i = 0; i < NAPOT_64K_PAGES; i++) {
        base_pte[i] = pte_val;
    }

    /* Flush G-stage TLB */
    hfence_gvma_all();
}

/* ===================================================================
 * VS-stage NAPOT PTE Installation
 * =================================================================== */

/*
 * vstage_napot_install_pte - Install a 64 KiB NAPOT PTE into VS-stage
 * @ctx:     two_stage_ctx_t (must have vs_ctx initialized)
 * @va:      Virtual address (must be 64 KiB aligned)
 * @pte_val: Pre-constructed NAPOT PTE value
 */
static void vstage_napot_install_pte(two_stage_ctx_t *ctx,
                                      uintptr_t va,
                                      uintptr_t pte_val) {
    uintptr_t base_va = va & ~NAPOT_64K_MASK;

    /* Create the page table path */
    pt_map_page(&ctx->vs_ctx, base_va, base_va,
                PTE_V | PTE_R | PTE_A | PTE_D, PT_LEVEL_4K);

    uintptr_t *base_pte = pt_get_pte(&ctx->vs_ctx, base_va, PT_LEVEL_4K);
    if (!base_pte) {
        LOG_E("vstage_napot_install_pte: could not get L0 PTE\n");
        return;
    }

    for (int i = 0; i < NAPOT_64K_PAGES; i++) {
        base_pte[i] = pte_val;
    }

    /* Flush VS-stage TLB */
    hfence_vvma_all();
}

/* ===================================================================
 * VS-mode Test Trampolines
 * =================================================================== */

/*
 * vs_access_all_16_pages - Write/read all 16 pages in a 64 KiB region
 * @base: Base address of the 64 KiB NAPOT region
 * Returns 0 on success, non-zero on failure (offset + error code).
 */
static uintptr_t vs_access_all_16_pages(uintptr_t base) {
    for (int i = 0; i < NAPOT_64K_PAGES; i++) {
        uintptr_t addr = base + (uintptr_t)i * PAGE_SIZE_4K;
        volatile uintptr_t *ptr = (volatile uintptr_t *)addr;
        uintptr_t expected = MAGIC_WRITE + (uintptr_t)i;

        *ptr = expected;
        uintptr_t val = *ptr;
        if (val != expected)
            return (uintptr_t)i * PAGE_SIZE_4K + 1;
    }
    return 0;
}

#endif /* HYPERVISOR_SVNAPOT_TEST_HELPERS_H */
