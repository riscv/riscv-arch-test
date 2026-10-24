/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef TWO_STAGE_H
#define TWO_STAGE_H

/* ===================================================================
 * Two-stage address translation context
 *
 * Wraps both translation stages:
 *   - VS-stage (vsatp): Sv39/Sv48/Sv57 or Bare (identity mapping)
 *   - G-stage  (hgatp): Sv39x4/Sv48x4/Sv57x4
 *
 * When vs_mode == SATP_MODE_BARE the VS-stage is disabled (identity).
 * When vs_mode is Sv39/48/57, VS-stage page tables are allocated from
 * the .page_tables pool and vsatp is programmed before VS-mode entry.
 * =================================================================== */

#include "vm/vm.h"
#include "gstage_pt.h"

typedef struct {
    int            vs_mode;     /* SATP_MODE_BARE or SV39/SV48/SV57 */
    pt_context_t   vs_ctx;      /* VS-stage page tables (unused when BARE) */
    gpt_context_t  g_ctx;       /* G-stage page tables */
} two_stage_ctx_t;

/* Initialize a two-stage context.
 * vs_mode: SATP_MODE_BARE (no VS-stage) or SATP_MODE_SV39/48/57.
 * g_mode:  HGATP_MODE_SV39X4/48X4/57X4. */
void two_stage_init(two_stage_ctx_t *ctx, int vs_mode, int g_mode);

/* Identity-map [base, base+size) at G-stage with the given level. */
int  two_stage_setup_identity(two_stage_ctx_t *ctx, uintptr_t base,
                              uintptr_t size, uintptr_t flags, int level);

/* Map (or override) a single G-stage page: GPA -> SPA at the given level.
 * Primary use case: override a specific page's flags after a bulk
 * identity mapping via two_stage_setup_identity. */
int  two_stage_g_map_page(two_stage_ctx_t *ctx, uintptr_t gpa,
                          uintptr_t spa, uintptr_t flags, int level);

/* Activate hgatp (and vsatp if non-Bare) in the current privilege mode
 * without entering VS-mode. Used by HLV/HLVX/HSV M-mode tests. */
void two_stage_enable(two_stage_ctx_t *ctx, unsigned vmid);

/* Activate hgatp (and vsatp if non-Bare), then run fn(arg) in VS-mode.
 * Returns whatever fn returns. */
uintptr_t two_stage_run_in_vs(two_stage_ctx_t *ctx,
                              uintptr_t (*fn)(uintptr_t),
                              uintptr_t arg);

/* Activate hgatp (and vsatp if non-Bare), then run fn(arg) in VU-mode.
 * Returns whatever fn returns. */
uintptr_t two_stage_run_in_vu(two_stage_ctx_t *ctx,
                              uintptr_t (*fn)(uintptr_t),
                              uintptr_t arg);

/* Disable both stages and reset state. */
void two_stage_cleanup(two_stage_ctx_t *ctx);

/* ===================================================================
 * VS-stage page table helpers (require vs_mode != BARE)
 * =================================================================== */

/* Map a single page in the VS-stage: VA -> GPA at the given level. */
int two_stage_vs_map(two_stage_ctx_t *ctx, uintptr_t va,
                     uintptr_t gpa, uintptr_t flags, int level);

/* Identity-map [base, base+size) in the VS-stage (VA == GPA). */
int two_stage_vs_identity(two_stage_ctx_t *ctx, uintptr_t base,
                          uintptr_t size, uintptr_t flags, int level);

/**
 * two_stage_vs_pt_page_addr - Get GPA of a VS-stage page table page
 *
 * Returns the physical address (== GPA under identity mapping) of the
 * page table page that contains the PTE for @va at @target_level.
 * This is the key API for HTVAL-IMP tests: it tells the caller which
 * GPA to mark as faulting in G-stage so that the VS-stage PTE walk
 * triggers a guest-page-fault.
 *
 * Returns 0 on error (e.g. PTE not yet allocated at that level).
 */
uintptr_t two_stage_vs_pt_page_addr(two_stage_ctx_t *ctx,
                                    uintptr_t va, int target_level);

#endif /* TWO_STAGE_H */
