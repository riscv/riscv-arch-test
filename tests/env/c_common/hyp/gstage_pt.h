/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef GSTAGE_PT_H
#define GSTAGE_PT_H

/* ===================================================================
 * G-stage page table management (Sv39x4 / Sv48x4 / Sv57x4)
 *
 * Mirrors common/vm/page_table.{h,c} but with the differences mandated
 * by the H extension:
 *   - Root page table is 16KB (4 contiguous 4KB pages), 16KB-aligned.
 *   - Top-level VPN is 11 bits (vs 9), so the root table holds
 *     2048 entries instead of 512.
 *   - All allocations come from a dedicated `.gpt_page_tables` pool.
 *
 * Permissions / leaf-PTE encoding match the regular Sv* page-table
 * format (PTE_V/R/W/X/U/A/D), so callers can reuse PTE_* macros from
 * vm/vm_defs.h.
 * =================================================================== */

#include "hyp_defs.h"
#include "vm/vm_defs.h"

/* ===================================================================
 * Common G-stage PTE flag set
 *
 * G-stage treats all accesses as U-mode, so leaf PTEs need U=1.
 * This combination covers full RWX + A/D (hardware or software
 * A/D update) and is the default "identity-mapped, fully accessible"
 * flag set used by all H-extension test setups.
 * =================================================================== */
#define G_FLAGS_RWXU_AD  (PTE_V|PTE_R|PTE_W|PTE_X|PTE_U|PTE_A|PTE_D)

/* G-stage page-table context */
typedef struct {
    int        mode;       /* HGATP_MODE_SV39X4 / SV48X4 / SV57X4 */
    int        levels;     /* SV39X4_LEVELS / SV48X4_LEVELS / SV57X4_LEVELS */
    uintptr_t *root_pt;    /* 16KB-aligned root (2048 entries) */
} gpt_context_t;

/* ----- Pool management ----- */

/* Reset the G-stage page-table pool allocator (invalidates all
 * previously allocated tables, including any roots). */
void gpt_pool_reset(void);

/* ----- Context lifecycle ----- */

/* Initialize a context for the given mode. Allocates a 16KB-aligned
 * root table from the pool. */
void gpt_init(gpt_context_t *ctx, int mode);

/* ----- Mapping API ----- */

/* Map a single page from GPA -> SPA at the given level.
 * Caller is responsible for setting U=1 (G-stage views all accesses
 * as U-mode), plus PTE_V plus permission bits. Returns 0 on success,
 * -1 on error. */
int gpt_map_page(gpt_context_t *ctx, uintptr_t gpa, uintptr_t spa,
                 uintptr_t flags, int level);

/* Identity-map [base, base+size) at the given page level, plus the
 * platform UART region for printf support. */
int gpt_setup_identity_mapping(gpt_context_t *ctx, uintptr_t base,
                               uintptr_t size, uintptr_t flags, int level);

/* Get pointer to the leaf PTE at the requested level (NULL if not
 * present). Useful for tweaking specific PTE bits before activating
 * translation. */
uintptr_t *gpt_get_pte(gpt_context_t *ctx, uintptr_t gpa, int level);

/* ----- Activation ----- */

/* Activate translation: write hgatp = MAKE_HGATP(mode, vmid, root_ppn)
 * and HFENCE.GVMA. */
void gpt_enable(gpt_context_t *ctx, unsigned vmid);

/* Switch hgatp back to Bare and HFENCE.GVMA. */
void gpt_disable(void);

#endif /* GSTAGE_PT_H */
