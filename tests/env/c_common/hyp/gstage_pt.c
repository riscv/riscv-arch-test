/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * common/hyp/gstage_pt.c — G-stage page table allocator and walker
 * =================================================================== */

#include "gstage_pt.h"
#include "hyp_csr.h"
#include "test_framework.h"

/* Pool boundaries provided by the linker script of each test target
 * (e.g. sv39x4/kernel.ld). The section is 16KB aligned, so its first
 * page is suitable as a root table. */
extern uintptr_t __gpt_pool_start;
extern uintptr_t __gpt_pool_end;

static uint8_t *_gpt_next = NULL;

/* ===================================================================
 * Pool helpers
 * =================================================================== */

static void gpt_pool_init_if_needed(void) {
    if (_gpt_next == NULL)
        _gpt_next = (uint8_t *)&__gpt_pool_start;
}

void gpt_pool_reset(void) {
    _gpt_next = (uint8_t *)&__gpt_pool_start;
}

/* Allocate `n_pages` of contiguous 4KB pages, aligned to `align_bytes`,
 * zero-filled. Returns NULL on exhaustion. */
static uintptr_t *gpt_alloc_aligned(unsigned n_pages, uintptr_t align_bytes) {
    gpt_pool_init_if_needed();

    uintptr_t cur = (uintptr_t)_gpt_next;
    uintptr_t aligned = (cur + align_bytes - 1) & ~(align_bytes - 1);
    uintptr_t next = aligned + (uintptr_t)n_pages * PAGE_SIZE_4K;

    if (next > (uintptr_t)&__gpt_pool_end) {
        LOG_E("gpt pool exhausted (need %u pages, align=0x%lx)\n",
              n_pages, (unsigned long)align_bytes);
        return NULL;
    }

    _gpt_next = (uint8_t *)next;

    /* Zero the allocated range */
    uintptr_t *p = (uintptr_t *)aligned;
    for (uintptr_t i = 0; i < ((uintptr_t)n_pages * PAGE_SIZE_4K) / sizeof(uintptr_t); i++)
        p[i] = 0;
    return p;
}

static uintptr_t *gpt_alloc_page(void) {
    return gpt_alloc_aligned(1, PAGE_SIZE_4K);
}

/* ===================================================================
 * Init
 * =================================================================== */

void gpt_init(gpt_context_t *ctx, int mode) {
    ctx->mode = mode;
    switch (mode) {
    case HGATP_MODE_SV39X4: ctx->levels = SV39X4_LEVELS; break;
    case HGATP_MODE_SV48X4: ctx->levels = SV48X4_LEVELS; break;
    case HGATP_MODE_SV57X4: ctx->levels = SV57X4_LEVELS; break;
    default:
        LOG_E("gpt_init: unsupported mode %d\n", mode);
        ctx->levels = SV39X4_LEVELS;
        break;
    }

    /* Allocate 16KB-aligned, 16KB-large root table. */
    ctx->root_pt = gpt_alloc_aligned(GPT_ROOT_PAGES, GPT_ROOT_ALIGN);
    if (!ctx->root_pt)
        LOG_E("gpt_init: failed to allocate root table\n");
}

/* ===================================================================
 * VPN extraction (G-stage)
 *
 * Top-level VPN is 11 bits (mask 0x7FF); intermediate / leaf levels
 * use the standard 9-bit mask.
 * =================================================================== */

static inline uintptr_t gpa_vpn(uintptr_t gpa, int level, int top_level) {
    uintptr_t shift = 12 + 9 * (uintptr_t)level;
    uintptr_t mask  = (level == top_level) ? GPA_VPN_TOP_MASK : VA_VPN_MASK;
    return (gpa >> shift) & mask;
}

static uintptr_t page_size_for_level(int level) {
    switch (level) {
    case PT_LEVEL_4K:    return PAGE_SIZE_4K;
    case PT_LEVEL_2M:    return PAGE_SIZE_2M;
    case PT_LEVEL_1G:    return PAGE_SIZE_1G;
    case PT_LEVEL_512G:  return (uintptr_t)(1ULL << 39);
    case PT_LEVEL_256T:  return (uintptr_t)(1ULL << 48);
    default:             return PAGE_SIZE_4K;
    }
}

/* ===================================================================
 * Map / lookup
 * =================================================================== */

int gpt_map_page(gpt_context_t *ctx, uintptr_t gpa, uintptr_t spa,
                 uintptr_t flags, int level) {
    if (!ctx || !ctx->root_pt) {
        LOG_E("gpt_map_page: NULL root\n");
        return -1;
    }
    uintptr_t pgsz = page_size_for_level(level);
    if ((gpa & (pgsz - 1)) != 0 || (spa & (pgsz - 1)) != 0) {
        LOG_E("gpt_map_page: misaligned gpa=0x%lx spa=0x%lx pgsz=0x%lx\n",
              (unsigned long)gpa, (unsigned long)spa, (unsigned long)pgsz);
        return -1;
    }

    uintptr_t *pt = ctx->root_pt;
    int top_level = ctx->levels - 1;

    for (int cur = top_level; cur > level; cur--) {
        uintptr_t idx = gpa_vpn(gpa, cur, top_level);
        uintptr_t pte = pt[idx];
        if (pte & PTE_V) {
            if (PTE_IS_LEAF(pte)) {
                LOG_E("gpt_map_page: leaf already at level %d for gpa 0x%lx\n",
                      cur, (unsigned long)gpa);
                return -1;
            }
            pt = (uintptr_t *)PTE_TO_PA(pte);
        } else {
            uintptr_t *new_pt = gpt_alloc_page();
            if (!new_pt) return -1;
            pt[idx] = PA_TO_PTE((uintptr_t)new_pt) | PTE_V;
            pt = new_pt;
        }
    }

    uintptr_t leaf_idx = gpa_vpn(gpa, level, top_level);
    pt[leaf_idx] = PA_TO_PTE(spa) | flags;
    return 0;
}

uintptr_t *gpt_get_pte(gpt_context_t *ctx, uintptr_t gpa, int level) {
    if (!ctx || !ctx->root_pt) return NULL;

    uintptr_t *pt = ctx->root_pt;
    int top_level = ctx->levels - 1;

    for (int cur = top_level; cur > level; cur--) {
        uintptr_t idx = gpa_vpn(gpa, cur, top_level);
        uintptr_t pte = pt[idx];
        if (!(pte & PTE_V) || PTE_IS_LEAF(pte))
            return NULL;
        pt = (uintptr_t *)PTE_TO_PA(pte);
    }
    return &pt[gpa_vpn(gpa, level, top_level)];
}

/* ===================================================================
 * Identity mapping
 * =================================================================== */

int gpt_setup_identity_mapping(gpt_context_t *ctx, uintptr_t base,
                               uintptr_t size, uintptr_t flags, int level) {
    uintptr_t pgsz = page_size_for_level(level);
    uintptr_t aligned_base = base & ~(pgsz - 1);
    uintptr_t end = (base + size + pgsz - 1) & ~(pgsz - 1);

    for (uintptr_t a = aligned_base; a < end; a += pgsz) {
        if (gpt_map_page(ctx, a, a, flags, level) != 0)
            return -1;
    }

    /* Map UART page so VS-mode printf works through G-stage. */
    uintptr_t uart_base = PLATFORM_UART0_BASE;
    if (uart_base < aligned_base || uart_base >= end) {
        uintptr_t uart_flags = PTE_V | PTE_R | PTE_W | PTE_U | PTE_A | PTE_D;
        (void)gpt_map_page(ctx, uart_base & ~(PAGE_SIZE_4K - 1),
                           uart_base & ~(PAGE_SIZE_4K - 1),
                           uart_flags, PT_LEVEL_4K);
    }
    return 0;
}

/* ===================================================================
 * hgatp activation
 * =================================================================== */

void gpt_enable(gpt_context_t *ctx, unsigned vmid) {
    uintptr_t root_ppn = ((uintptr_t)ctx->root_pt) >> PAGE_SHIFT;
    hgatp_set(ctx->mode, vmid, root_ppn);
}

void gpt_disable(void) {
    hgatp_set_bare();
}
