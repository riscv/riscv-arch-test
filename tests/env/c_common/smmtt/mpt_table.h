/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef MPT_TABLE_H
#define MPT_TABLE_H

/* ===================================================================
 * Smmpt Memory Protection Table (MPT) builder
 *
 * Builds the memory-resident radix tree of memory-protection-table
 * entries (MPTEs) described in SPEC/riscv-smmtt/chapter4.adoc and
 * activates it through the Smsd `mmpt` CSR (chapter3.adoc).
 *
 * The MPT is analogous to a page table but grants XWR access-type
 * permissions on *physical* addresses (SPA) for privilege modes < M.
 * Tables are allocated from a linker-reserved, page-aligned pool
 * (.mpt_tables) with a bump allocator, mirroring common/vm.
 *
 * A leaf MPTE holds 2^NUMPGINRANGE XWR tuples (8 for Smmpt34, 16 for
 * the RV64 modes); a level-0 leaf therefore covers 16 (or 8) 4 KiB
 * pages, one per tuple.
 * =================================================================== */

#include "smmtt_insn.h"

/* MPT table pool boundaries (provided by the suite linker script). */
extern uintptr_t __mpt_pool_start;
extern uintptr_t __mpt_pool_end;

typedef struct {
    mpt_mode_info_t info;   /* radix parameters for the selected mode   */
    uintptr_t       root_pa;/* physical address of the root MPT table   */
} mpt_ctx_t;

/* ------------------------------------------------------------------ */
/* Pool management                                                     */
/* ------------------------------------------------------------------ */

/* Reset the bump allocator; invalidates every previously built MPT. */
void mpt_pool_reset(void);

/* ------------------------------------------------------------------ */
/* Context setup                                                       */
/* ------------------------------------------------------------------ */

/* Initialize @ctx for @mode (MMPT_MODE_SMMPT*) and allocate its root
 * table. Returns 0 on success, -1 on unknown mode / pool exhaustion. */
int mpt_init(mpt_ctx_t *ctx, int mode);

/* ------------------------------------------------------------------ */
/* Table construction                                                  */
/* ------------------------------------------------------------------ */

/* Walk from the root toward @pa, creating non-leaf MPTEs (and the
 * intermediate tables they point to) down to @level, and return a
 * pointer to the MPTE at @level (indexed by pn[level]). Returns NULL
 * on pool exhaustion. Used to install or corrupt a specific MPTE. */
uintptr_t *mpt_walk_create(mpt_ctx_t *ctx, uintptr_t pa, int level);

/* Install a non-NAPOT leaf MPTE at @leaf_level covering @pa, with the
 * 2^NUMPGINRANGE XWR tuples taken from @xwr (xwr[0..npg_tuples-1]).
 * Returns 0 on success, -1 on error. */
int mpt_map_leaf(mpt_ctx_t *ctx, uintptr_t pa, int leaf_level,
                 const unsigned int *xwr);

/* Set the XWR tuple of a single 4 KiB page @pa using a level-0 leaf,
 * leaving the other tuples of that leaf untouched. A freshly created
 * leaf defaults every tuple to MPT_XWR_NONE (no access). */
int mpt_set_page(mpt_ctx_t *ctx, uintptr_t pa, unsigned int xwr);

/* Map [base, base+size) at 4 KiB granularity with a uniform @xwr. */
int mpt_map_range(mpt_ctx_t *ctx, uintptr_t base, uintptr_t size,
                  unsigned int xwr);

/* Install a NAPOT leaf (L=1,N=1) at @leaf_level for @pa: writes the
 * 2^(g+1) contiguous, identical MPTEs of the NAPOT range with the
 * given single @xwr tuple and @g encoding. */
int mpt_map_napot(mpt_ctx_t *ctx, uintptr_t pa, int leaf_level,
                  unsigned int xwr, unsigned int g);

/* Overwrite the MPTE covering @pa at @level with a raw value (used to
 * inject V=0, reserved-bit, reserved-encoding and L/N corruptions). */
int mpt_write_raw(mpt_ctx_t *ctx, uintptr_t pa, int level, uintptr_t raw);

/* ------------------------------------------------------------------ */
/* Activation                                                          */
/* ------------------------------------------------------------------ */

/* Write mmpt = {PPN=root_pa>>12, MODE=ctx->mode} and issue a global
 * MFENCE.PA so subsequent implicit MPT reads observe the new tree. */
void mpt_activate(mpt_ctx_t *ctx);

/* Write mmpt.MODE = Bare (PPN = 0) and issue a global MFENCE.PA,
 * disabling MPT checking. */
void mpt_deactivate(void);

/* ------------------------------------------------------------------ */
/* mmpt CSR helpers                                                    */
/* ------------------------------------------------------------------ */

static inline uintptr_t mmpt_read(void)          { return MMPT_READ(); }
static inline void      mmpt_write(uintptr_t v)  { MMPT_WRITE(v); }
static inline uintptr_t mmpt_get_mode(uintptr_t v) { return MMPT_GET_MODE(v); }

/* Probe whether @mode is accepted by mmpt.MODE (WARL). Writes
 * MODE=@mode with PPN=0, reads back the MODE field, restores Bare.
 * Returns true if the read-back MODE equals @mode. */
bool mpt_probe_mode(int mode);

#endif /* MPT_TABLE_H */
