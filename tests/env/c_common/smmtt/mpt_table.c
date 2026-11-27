/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#include "mpt_table.h"
#include "test_framework.h"

/* ===================================================================
 * Per-mode radix parameters (chapter4)
 *
 * On an RV64 build only Smmpt43/52/64 exist; on an RV32 build only
 * Smmpt34 exists. MPTESIZE always equals sizeof(uintptr_t) for the
 * modes valid on that XLEN, so tables are handled as uintptr_t arrays.
 * =================================================================== */

int mpt_mode_info(int mode, mpt_mode_info_t *info) {
    switch (mode) {
#if __riscv_xlen == 64
    case MMPT_MODE_SMMPT43:
        info->mode = mode; info->levels = 3; info->mpte_size = 8;
        info->numpginrange = 4; info->npg_tuples = 16;
        info->offset_bits = 16; info->spa_bits = 43;
        return 0;
    case MMPT_MODE_SMMPT52:
        info->mode = mode; info->levels = 4; info->mpte_size = 8;
        info->numpginrange = 4; info->npg_tuples = 16;
        info->offset_bits = 16; info->spa_bits = 52;
        return 0;
    case MMPT_MODE_SMMPT64:
        info->mode = mode; info->levels = 5; info->mpte_size = 8;
        info->numpginrange = 4; info->npg_tuples = 16;
        info->offset_bits = 16; info->spa_bits = 64;
        return 0;
#else
    case MMPT_MODE_SMMPT34:
        info->mode = mode; info->levels = 2; info->mpte_size = 4;
        info->numpginrange = 3; info->npg_tuples = 8;
        info->offset_bits = 15; info->spa_bits = 34;
        return 0;
#endif
    default:
        return -1;
    }
}

int mpt_pn_shift(int mode, int level) {
    (void)mode;
#if __riscv_xlen == 32
    return (level == 0) ? 15 : 25;   /* Smmpt34: pn[0]=bits[24:15], pn[1]=bits[33:25] */
#else
    return 16 + 9 * level;           /* Smmpt43/52/64: pn[i] starts at bit 16+9i */
#endif
}

int mpt_pn_width(int mode, int level) {
#if __riscv_xlen == 32
    (void)mode;
    return (level == 0) ? 10 : 9;    /* Smmpt34 root=2^9, level-0 table=2^10 */
#else
    if (mode == MMPT_MODE_SMMPT64 && level == 4)
        return 12;                   /* Smmpt64 root table has 2^12 entries */
    return 9;
#endif
}

uintptr_t mpt_pn(int mode, uintptr_t pa, int level) {
    int w = mpt_pn_width(mode, level);
    uintptr_t mask = ((uintptr_t)1 << w) - 1;
    return (pa >> mpt_pn_shift(mode, level)) & mask;
}

uintptr_t mpt_level_entries(int mode, int level) {
    return (uintptr_t)1 << mpt_pn_width(mode, level);
}

uintptr_t mpt_page_index(const mpt_mode_info_t *info, uintptr_t pa, int leaf_level) {
    uintptr_t mask = ((uintptr_t)1 << info->numpginrange) - 1;
    if (leaf_level == 0) {
        /* NUMPGINRANGE MSBs of the range offset. offset_bits - numpginrange
         * is 12 for every mode, so this is the 4 KiB page number masked. */
        return (pa >> MPT_PAGESHIFT) & mask;
    }
    /* NUMPGINRANGE MSBs of pn[leaf_level-1]. */
    int w = mpt_pn_width(info->mode, leaf_level - 1);
    uintptr_t pn = mpt_pn(info->mode, pa, leaf_level - 1);
    return (pn >> (w - info->numpginrange)) & mask;
}

/* ===================================================================
 * Table pool - static bump allocator (mirrors common/vm/page_table.c)
 * =================================================================== */

static uintptr_t mpt_pool_next;

void mpt_pool_reset(void) {
    mpt_pool_next = (uintptr_t)&__mpt_pool_start;
}

static uintptr_t mpt_pool_alloc(uintptr_t align, uintptr_t size) {
    if (mpt_pool_next == 0)
        mpt_pool_next = (uintptr_t)&__mpt_pool_start;

    uintptr_t p = (mpt_pool_next + align - 1) & ~(align - 1);
    if (p + size > (uintptr_t)&__mpt_pool_end) {
        LOG_E("MPT table pool exhausted\n");
        return 0;
    }
    mpt_pool_next = p + size;

    for (uintptr_t a = p; a < p + size; a += sizeof(uintptr_t))
        *(uintptr_t *)a = 0;
    return p;
}

/* Allocate one MPT table. Every table is page-aligned and page-sized,
 * except the Smmpt64 root which is 32 KiB-sized and 32 KiB-aligned. */
static uintptr_t mpt_alloc_table(mpt_ctx_t *ctx, bool is_root) {
#if __riscv_xlen == 64
    if (is_root && ctx->info.mode == MMPT_MODE_SMMPT64)
        return mpt_pool_alloc(0x8000UL, 0x8000UL);
#else
    (void)ctx; (void)is_root;
#endif
    return mpt_pool_alloc(MPT_PAGESIZE, MPT_PAGESIZE);
}

/* ===================================================================
 * Context setup
 * =================================================================== */

int mpt_init(mpt_ctx_t *ctx, int mode) {
    if (mpt_mode_info(mode, &ctx->info) != 0) {
        LOG_E("unsupported MPT mode %d\n", mode);
        return -1;
    }
    ctx->root_pa = mpt_alloc_table(ctx, true);
    if (!ctx->root_pa) {
        LOG_E("failed to allocate MPT root table\n");
        return -1;
    }
    return 0;
}

/* ===================================================================
 * Table construction
 * =================================================================== */

uintptr_t *mpt_walk_create(mpt_ctx_t *ctx, uintptr_t pa, int level) {
    uintptr_t table_pa = ctx->root_pa;

    for (int cur = ctx->info.levels - 1; cur > level; cur--) {
        uintptr_t *tbl = (uintptr_t *)table_pa;
        uintptr_t idx = mpt_pn(ctx->info.mode, pa, cur);
        uintptr_t v = tbl[idx];

        if (!(v & MPTE_V)) {
            uintptr_t nt = mpt_alloc_table(ctx, false);
            if (!nt)
                return NULL;
            tbl[idx] = MPTE_NONLEAF(nt);
            v = tbl[idx];
        }
        if (v & MPTE_L)
            return NULL;   /* a leaf blocks descent to a deeper level */

        table_pa = (v >> MPTE_PPN_SHIFT) << MPT_PAGESHIFT;
    }

    uintptr_t *tbl = (uintptr_t *)table_pa;
    return &tbl[mpt_pn(ctx->info.mode, pa, level)];
}

int mpt_map_leaf(mpt_ctx_t *ctx, uintptr_t pa, int leaf_level,
                 const unsigned int *xwr) {
    uintptr_t *mpte = mpt_walk_create(ctx, pa, leaf_level);
    if (!mpte)
        return -1;

    uintptr_t v = MPTE_V | MPTE_L;   /* N=0: non-NAPOT leaf */
    for (int k = 0; k < ctx->info.npg_tuples; k++)
        v |= MPTE_XWR_FIELD(k, xwr[k]);
    *mpte = v;
    return 0;
}

int mpt_set_page(mpt_ctx_t *ctx, uintptr_t pa, unsigned int xwr) {
    uintptr_t *mpte = mpt_walk_create(ctx, pa, 0);
    if (!mpte)
        return -1;

    uintptr_t v = *mpte;
    if (!(v & MPTE_V) || (v & MPTE_N))
        v = MPTE_V | MPTE_L;         /* (re)init as a non-NAPOT leaf */
    v |= MPTE_L;

    uintptr_t pi = mpt_page_index(&ctx->info, pa, 0);
    v &= ~((uintptr_t)0x7 << (MPTE_XWR_BASE + 3 * pi));
    v |= MPTE_XWR_FIELD(pi, xwr);
    *mpte = v;
    return 0;
}

int mpt_map_range(mpt_ctx_t *ctx, uintptr_t base, uintptr_t size,
                  unsigned int xwr) {
    for (uintptr_t a = base; a < base + size; a += MPT_PAGESIZE)
        if (mpt_set_page(ctx, a, xwr) != 0)
            return -1;
    return 0;
}

int mpt_map_napot(mpt_ctx_t *ctx, uintptr_t pa, int leaf_level,
                  unsigned int xwr, unsigned int g) {
    uintptr_t *mpte = mpt_walk_create(ctx, pa, leaf_level);
    if (!mpte)
        return -1;

    uintptr_t count = (uintptr_t)1 << (g + 1);
    uintptr_t idx = mpt_pn(ctx->info.mode, pa, leaf_level);
    uintptr_t base_idx = idx & ~(count - 1);
    uintptr_t *tbl = mpte - idx;
    uintptr_t v = MPTE_NAPOT_LEAF(xwr, g);

    uintptr_t entries = mpt_level_entries(ctx->info.mode, leaf_level);
    if (base_idx + count > entries)
        return -1;                   /* range would overflow the table */

    for (uintptr_t k = 0; k < count; k++)
        tbl[base_idx + k] = v;
    return 0;
}

int mpt_write_raw(mpt_ctx_t *ctx, uintptr_t pa, int level, uintptr_t raw) {
    uintptr_t *mpte = mpt_walk_create(ctx, pa, level);
    if (!mpte)
        return -1;
    *mpte = raw;
    return 0;
}

/* ===================================================================
 * Activation
 * =================================================================== */

void mpt_activate(mpt_ctx_t *ctx) {
    mmpt_write(MMPT_MAKE(ctx->info.mode, 0, ctx->root_pa >> MPT_PAGESHIFT));
    MFENCE_PA_GG();
}

void mpt_deactivate(void) {
    mmpt_write(MMPT_MAKE(MMPT_MODE_BARE, 0, 0));
    MFENCE_PA_GG();
}

bool mpt_probe_mode(int mode) {
    mmpt_write(MMPT_MAKE(mode, 0, 0));
    uintptr_t rb = mmpt_get_mode(mmpt_read());
    /* Leave mmpt disabled and deterministic for the next probe/test. */
    mmpt_write(MMPT_MAKE(MMPT_MODE_BARE, 0, 0));
    return rb == (uintptr_t)mode;
}
