/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#include "vm.h"
#include "test_framework.h"

/* ===================================================================
 * Page Table Pool - Static Bump Allocator
 *
 * Pages are allocated from a statically reserved region defined
 * in the linker script (.page_tables section). A simple bump
 * pointer tracks the next free page.
 * =================================================================== */

/* Linker-provided page table pool boundaries */
extern uintptr_t __page_tables_start;
extern uintptr_t __page_tables_end;

/* Bump allocator state */
static uintptr_t *pt_pool_next = NULL;

/**
 * pt_pool_init - Initialize the page table pool (called once)
 */
static void pt_pool_init(void) {
    if (pt_pool_next == NULL)
        pt_pool_next = (uintptr_t *)&__page_tables_start;
}

/**
 * pt_pool_reset - Reset the page table pool allocator
 *
 * All previously allocated page tables become invalid.
 */
void pt_pool_reset(void) {
    pt_pool_next = (uintptr_t *)&__page_tables_start;
}

/**
 * pt_alloc_page - Allocate one 4KB page from the pool
 *
 * Returns a pointer to a zeroed 4KB-aligned page, or NULL if
 * the pool is exhausted.
 */
static uintptr_t *pt_alloc_page(void) {
    pt_pool_init();

    uintptr_t *page = pt_pool_next;
    uintptr_t *next = (uintptr_t *)((uintptr_t)page + PAGE_SIZE);

    if ((uintptr_t)next > (uintptr_t)&__page_tables_end) {
        LOG_E("page table pool exhausted\n");
        return NULL;
    }

    pt_pool_next = next;

    /* Zero the page */
    uintptr_t *p = page;
    for (int i = 0; i < (int)(PAGE_SIZE / sizeof(uintptr_t)); i++)
        p[i] = 0;

    return page;
}

/* ===================================================================
 * Page Table Initialization
 * =================================================================== */

/**
 * pt_init - Initialize a page table context
 */
void pt_init(pt_context_t *ctx, int mode) {
    ctx->mode = mode;
    ctx->map_base = 0;
    ctx->map_size = 0;
    ctx->map_level = PT_LEVEL_1G;

    switch (mode) {
    case SATP_MODE_SV39:
        ctx->levels = SV39_LEVELS;
        break;
    case SATP_MODE_SV48:
        ctx->levels = SV48_LEVELS;
        break;
    case SATP_MODE_SV57:
        ctx->levels = SV57_LEVELS;
        break;
    default:
        LOG_E("unsupported satp mode %d\n", mode);
        ctx->levels = SV39_LEVELS;
        break;
    }

    ctx->root_pt = pt_alloc_page();
    if (!ctx->root_pt)
        LOG_E("failed to allocate root page table\n");
}

/**
 * pt_destroy - Release page table resources
 */
void pt_destroy(pt_context_t *ctx) {
    ctx->root_pt = NULL;
    ctx->levels = 0;
    ctx->mode = SATP_MODE_BARE;
    /* Note: pool is NOT reset here to allow multiple contexts.
     * Call pt_pool_reset() explicitly when all contexts are done. */
}

/* ===================================================================
 * Page Table Mapping
 * =================================================================== */

/**
 * page_size_for_level - Get the page size for a given level
 */
static uintptr_t page_size_for_level(int level) {
    switch (level) {
    case PT_LEVEL_4K:   return PAGE_SIZE_4K;
    case PT_LEVEL_2M:   return PAGE_SIZE_2M;
    case PT_LEVEL_1G:   return PAGE_SIZE_1G;
    case PT_LEVEL_512G: return (uintptr_t)(1ULL << 39);
    case PT_LEVEL_256T: return (uintptr_t)(1ULL << 48);
    default:            return PAGE_SIZE_4K;
    }
}

/**
 * pt_map_page - Map a single page at the specified level
 *
 * Walks the page table from the root, creating intermediate
 * page table pages as needed, and installs a leaf PTE at
 * the target level.
 *
 * @ctx:   Page table context
 * @va:    Virtual address (must be aligned to page size at @level)
 * @pa:    Physical address (must be aligned to page size at @level)
 * @flags: PTE flags (must include PTE_V)
 * @level: Target level (PT_LEVEL_4K=0, PT_LEVEL_2M=1, PT_LEVEL_1G=2,
 *         PT_LEVEL_512G=3 for Sv48+, PT_LEVEL_256T=4 for Sv57)
 *
 * Returns 0 on success, -1 on error.
 */
int pt_map_page(pt_context_t *ctx, uintptr_t va, uintptr_t pa,
                uintptr_t flags, int level) {
    uintptr_t pgsz = page_size_for_level(level);

    /* Alignment check */
    if ((va & (pgsz - 1)) != 0) {
        LOG_E("pt_map_page: VA 0x%lx not aligned to 0x%lx\n",
              (unsigned long)va, (unsigned long)pgsz);
        return -1;
    }
    if ((pa & (pgsz - 1)) != 0) {
        LOG_E("pt_map_page: PA 0x%lx not aligned to 0x%lx\n",
              (unsigned long)pa, (unsigned long)pgsz);
        return -1;
    }

    if (!ctx->root_pt) {
        LOG_E("pt_map_page: root page table is NULL\n");
        return -1;
    }

    /*
     * Walk from the highest level down to the target level.
     *
     * For Sv39 (3 levels): root is level 2, walk levels 2 -> 1 -> 0
     * For Sv48 (4 levels): root is level 3, walk levels 3 -> 2 -> 1 -> 0
     * For Sv57 (5 levels): root is level 4, walk levels 4 -> 3 -> 2 -> 1 -> 0
     *
     * The root page table corresponds to (ctx->levels - 1).
     * We walk down until we reach the target level.
     */
    uintptr_t *pt = ctx->root_pt;
    int top_level = ctx->levels - 1;

    for (int cur_level = top_level; cur_level > level; cur_level--) {
        uintptr_t vpn = VA_VPN(va, cur_level);
        uintptr_t pte = pt[vpn];

        if (pte & PTE_V) {
            /* PTE exists */
            if (PTE_IS_LEAF(pte)) {
                /* Already a leaf at a higher level - conflict */
                LOG_E("pt_map_page: existing leaf PTE at level %d "
                      "for VA 0x%lx\n", cur_level, (unsigned long)va);
                return -1;
            }
            /* Non-leaf: follow to next level */
            pt = (uintptr_t *)PTE_TO_PA(pte);
        } else {
            /* Allocate a new page table page */
            uintptr_t *new_pt = pt_alloc_page();
            if (!new_pt) {
                LOG_E("pt_map_page: failed to allocate PT page "
                      "at level %d\n", cur_level);
                return -1;
            }
            /* Install non-leaf PTE (V=1, no R/W/X) */
            pt[vpn] = PA_TO_PTE((uintptr_t)new_pt) | PTE_V;
            pt = new_pt;
        }
    }

    /* Install the leaf PTE at the target level */
    uintptr_t vpn = VA_VPN(va, level);
    pt[vpn] = PA_TO_PTE(pa) | flags;

    return 0;
}

/* ===================================================================
 * Debug: dump page table entries
 * =================================================================== */

/**
 * pt_dump - Print page table entries for debugging
 */
void pt_dump(pt_context_t *ctx) {
    if (!ctx || !ctx->root_pt) {
        LOG_E("pt_dump: NULL context\n");
        return;
    }

    LOG_D("Page table dump (mode=%d, levels=%d, root=0x%lx):\n",
          ctx->mode, ctx->levels, (unsigned long)ctx->root_pt);

    uintptr_t *root = ctx->root_pt;
    int top_level = ctx->levels - 1;

    for (int i = 0; i < PT_ENTRIES; i++) {
        if (root[i] & PTE_V) {
            uintptr_t pte = root[i];
            LOG_D("L%d[%3d] = 0x%016lx (PA=0x%lx, flags=%s%s%s%s%s%s%s%s)\n",
                   top_level, i, (unsigned long)pte,
                   (unsigned long)PTE_TO_PA(pte),
                   (pte & PTE_V) ? "V" : "",
                   (pte & PTE_R) ? "R" : "",
                   (pte & PTE_W) ? "W" : "",
                   (pte & PTE_X) ? "X" : "",
                   (pte & PTE_U) ? "U" : "",
                   (pte & PTE_G) ? "G" : "",
                   (pte & PTE_A) ? "A" : "",
                   (pte & PTE_D) ? "D" : "");
        }
    }
}

/* ===================================================================
 * Identity Mapping
 * =================================================================== */

/**
 * pt_setup_identity_mapping - Create VA=PA identity mapping
 *
 * Maps the region [base, base+size) with VA = PA using the
 * specified page level. Also maps the UART I/O region for
 * S-mode printf support.
 */
int pt_setup_identity_mapping(pt_context_t *ctx, uintptr_t base,
                              uintptr_t size, uintptr_t flags, int level) {
    uintptr_t pgsz = page_size_for_level(level);

    /* Align base down and size up to page boundary */
    uintptr_t aligned_base = base & ~(pgsz - 1);
    uintptr_t end = (base + size + pgsz - 1) & ~(pgsz - 1);

    /* Record mapping parameters for vm_switch_mode */
    ctx->map_base = aligned_base;
    ctx->map_size = end - aligned_base;
    ctx->map_level = level;

    /* Map the main memory region */
    for (uintptr_t addr = aligned_base; addr < end; addr += pgsz) {
        int ret = pt_map_page(ctx, addr, addr, flags, level);
        if (ret != 0) {
            LOG_E("identity mapping failed at 0x%lx\n",
                  (unsigned long)addr);
            return -1;
        }
    }

    /*
     * Map UART I/O region for S-mode printf support.
     * UART is typically at 0x10000000, which is below RAM.
     * We map one page at 4KB granularity (UART is memory-mapped I/O).
     */
    uintptr_t uart_base = PLATFORM_UART0_BASE;
    uintptr_t uart_flags = PTE_V | PTE_R | PTE_W | PTE_A | PTE_D;

    /* Only map UART if it's not already covered by the main mapping */
    if (uart_base < aligned_base || uart_base >= end) {
        int ret = pt_map_page(ctx, uart_base, uart_base, uart_flags, PT_LEVEL_4K);
        if (ret != 0) {
            LOG_W("failed to map UART at 0x%lx\n",
                  (unsigned long)uart_base);
            /* Non-fatal: continue without UART mapping */
        }
    }

    /*
     * Map CLINT region if defined (for timer access in S-mode).
     */
#ifdef PLATFORM_CLINT_BASE
    uintptr_t clint_base = PLATFORM_CLINT_BASE;
    if (clint_base < aligned_base || clint_base >= end) {
        /* Map 64KB for CLINT (covers all CLINT registers) */
        uintptr_t clint_flags = PTE_V | PTE_R | PTE_W | PTE_A | PTE_D;
        (void)pt_map_page(ctx, clint_base, clint_base, clint_flags, PT_LEVEL_4K);
    }
#endif

    /*
     * Map test device region if defined (for QEMU exit).
     */
#ifdef PLATFORM_TEST_DEVICE
    uintptr_t test_dev = PLATFORM_TEST_DEVICE;
    if (test_dev < aligned_base || test_dev >= end) {
        uintptr_t dev_flags = PTE_V | PTE_R | PTE_W | PTE_A | PTE_D;
        (void)pt_map_page(ctx, test_dev, test_dev, dev_flags, PT_LEVEL_4K);
    }
#endif

    return 0;
}

/* ===================================================================
 * pt_get_pte - Get pointer to a PTE at a specific level
 *
 * Combines get_pt_page_addr() with VPN indexing to return a direct
 * pointer to the PTE entry for the given VA at the target level.
 * =================================================================== */
uintptr_t *pt_get_pte(pt_context_t *ctx, uintptr_t va, int level) {
    uintptr_t pt_page = get_pt_page_addr(ctx, va, level);
    if (pt_page == 0)
        return NULL;
    uintptr_t *pt = (uintptr_t *)pt_page;
    return &pt[VA_VPN(va, level)];
}

/* ===================================================================
 * get_pt_page_addr - Walk page table to find PT page at target level
 *
 * For Sv39 with 3 levels (L2=root, L1=middle, L0=leaf):
 *   target_level=2 -> returns root PT page address
 *   target_level=1 -> returns L1 PT page address
 *   target_level=0 -> returns L0 PT page address
 *
 * Works for any Sv mode (Sv39/Sv48/Sv57) since it uses ctx->levels.
 * =================================================================== */
uintptr_t get_pt_page_addr(pt_context_t *ctx, uintptr_t va, int target_level) {
    if (!ctx || !ctx->root_pt)
        return 0;

    int levels = ctx->levels;  /* 3 for Sv39, 4 for Sv48, 5 for Sv57 */
    uintptr_t *pt = ctx->root_pt;

    /* Walk from root (highest level) down to target_level */
    for (int level = levels - 1; level > target_level; level--) {
        unsigned int vpn = VA_VPN(va, level);
        uintptr_t pte = pt[vpn];

        if (!(pte & PTE_V))
            return 0;  /* Invalid PTE */

        if (PTE_IS_LEAF(pte))
            return 0;  /* Hit a leaf before reaching target level */

        /* Follow pointer to next level page table */
        pt = (uintptr_t *)PTE_TO_PA(pte);
    }

    return (uintptr_t)pt;
}

uintptr_t pte_read(pt_context_t *ctx, uintptr_t va, int level) {
    uintptr_t *p = pt_get_pte(ctx, va, level);
    return p ? *p : 0;
}

void pte_set_bits(pt_context_t *ctx, uintptr_t va, int level,
                  uintptr_t bits) {
    uintptr_t *p = pt_get_pte(ctx, va, level);
    if (p) {
        *p |= bits;
        vm_sfence_vma(0, 0);
    }
}

void pte_clear_bits(pt_context_t *ctx, uintptr_t va, int level,
                    uintptr_t bits) {
    uintptr_t *p = pt_get_pte(ctx, va, level);
    if (p) {
        *p &= ~bits;
        vm_sfence_vma(0, 0);
    }
}

void pte_write(pt_context_t *ctx, uintptr_t va, int level,
               uintptr_t value) {
    uintptr_t *p = pt_get_pte(ctx, va, level);
    if (p) {
        *p = value;
        vm_sfence_vma(0, 0);
    }
}

void vm_fill_exec_page(uintptr_t addr) {
    uint32_t *p = (uint32_t *)addr;
    for (int i = 0; i < 1024 - 1; i++)
        p[i] = 0x00000013;  /* nop (addi x0, x0, 0) */
    p[1023] = 0x00008067;   /* ret (jalr x0, ra, 0) */
}

int vm_setup_code_mapping(pt_context_t *ctx, uintptr_t page_size,
                          const uintptr_t *regions, unsigned int n_regions) {
    uintptr_t flags = PTE_V | PTE_R | PTE_W | PTE_X | PTE_A | PTE_D;
    uintptr_t base = PLATFORM_MEM_BASE & ~(page_size - 1);

    /* end = (max region aligned down to page_size) + 2 * page_size, so the
     * block right after the last test region is also covered. */
    uintptr_t end = base;
    for (unsigned int i = 0; i < n_regions; i++) {
        uintptr_t r = regions[i] & ~(page_size - 1);
        if (r + 2 * page_size > end)
            end = r + 2 * page_size;
    }

    for (uintptr_t addr = base; addr < end; addr += page_size) {
        int is_region = 0;
        for (unsigned int i = 0; i < n_regions; i++) {
            if (addr == (regions[i] & ~(page_size - 1))) {
                is_region = 1;
                break;
            }
        }
        if (is_region)
            continue;
        int ret = pt_map_page(ctx, addr, addr, flags, PT_LEVEL_2M);
        if (ret != 0)
            return ret;
    }

    /* Map UART I/O region for S-mode printf support */
    uintptr_t uart_flags = PTE_V | PTE_R | PTE_W | PTE_A | PTE_D;
    pt_map_page(ctx, PLATFORM_UART0_BASE, PLATFORM_UART0_BASE,
                uart_flags, PT_LEVEL_4K);

    return 0;
}
