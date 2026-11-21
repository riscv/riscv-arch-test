/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef VM_H
#define VM_H

/* ===================================================================
 * RISC-V Virtual Memory Support
 *
 * Unified interface for page table management, satp mode switching,
 * and S-mode execution with virtual memory enabled.
 *
 * Supports Sv39 (3-level), Sv48 (4-level), and Sv57 (5-level)
 * page table configurations with configurable page sizes (4K/2M/1G).
 * =================================================================== */

#include "vm_defs.h"
#include "encoding.h"

/* ===================================================================
 * Page Table Context
 *
 * Holds all state needed to manage a set of page tables.
 * Each context represents one address space configuration.
 * =================================================================== */
typedef struct {
    int         mode;       /* SATP_MODE_SV39 / SV48 / SV57          */
    uintptr_t  *root_pt;   /* Root page table physical address       */
    int         levels;     /* Number of page table levels (3/4/5)    */
    uintptr_t   map_base;  /* Identity mapping base address          */
    uintptr_t   map_size;  /* Identity mapping size                  */
    int         map_level;  /* Page level used for identity mapping   */
} pt_context_t;

/* ===================================================================
 * Page Table Management API
 * =================================================================== */

/**
 * pt_init - Initialize a page table context
 * @ctx:  Page table context to initialize
 * @mode: satp mode (SATP_MODE_SV39, SATP_MODE_SV48, SATP_MODE_SV57)
 *
 * Allocates a root page table from the page table pool and sets up
 * the context for the specified translation mode.
 */
void pt_init(pt_context_t *ctx, int mode);

/**
 * pt_destroy - Release page table resources
 * @ctx: Page table context to destroy
 *
 * Resets the page table pool. Note: this invalidates ALL page table
 * contexts since the pool is shared.
 */
void pt_destroy(pt_context_t *ctx);

/**
 * pt_map_page - Map a single page (4K, 2M, or 1G)
 * @ctx:   Page table context
 * @va:    Virtual address (must be aligned to page size at @level)
 * @pa:    Physical address (must be aligned to page size at @level)
 * @flags: PTE flags (PTE_V | PTE_R | PTE_W | PTE_X | PTE_U | PTE_A | PTE_D)
 * @level: Page level (PT_LEVEL_4K, PT_LEVEL_2M, PT_LEVEL_1G)
 *
 * Creates a mapping from @va to @pa with the specified permissions.
 * Intermediate page table pages are allocated automatically.
 *
 * Returns 0 on success, -1 on error (alignment, pool exhausted).
 */
int pt_map_page(pt_context_t *ctx, uintptr_t va, uintptr_t pa,
                uintptr_t flags, int level);

/**
 * pt_setup_identity_mapping - Create identity mapping (VA = PA)
 * @ctx:   Page table context
 * @base:  Base physical address (must be aligned to page size at @level)
 * @size:  Size of region to map
 * @flags: PTE flags for all mapped pages
 * @level: Page level (PT_LEVEL_4K, PT_LEVEL_2M, PT_LEVEL_1G)
 *
 * Maps the region [base, base+size) with VA = PA.
 * Also maps the UART I/O region for S-mode printf support.
 *
 * Returns 0 on success, -1 on error.
 */
int pt_setup_identity_mapping(pt_context_t *ctx, uintptr_t base,
                              uintptr_t size, uintptr_t flags, int level);

/**
 * pt_pool_reset - Reset the page table pool allocator
 *
 * Frees all allocated page table pages. All existing page table
 * contexts become invalid after this call.
 */
void pt_pool_reset(void);

/* ===================================================================
 * satp Control API
 * =================================================================== */

/**
 * vm_enable - Enable virtual memory
 * @ctx:  Page table context (must be initialized with mappings)
 * @asid: Address Space Identifier (0 for no ASID)
 *
 * Writes the satp CSR and executes sfence.vma to flush the TLB.
 * Must be called from M-mode (satp takes effect in S/U-mode).
 */
void vm_enable(pt_context_t *ctx, unsigned asid);

/**
 * vm_disable - Disable virtual memory
 *
 * Sets satp to Bare mode (MODE=0) and flushes the TLB.
 */
void vm_disable(void);

/**
 * vm_sfence_vma - Execute sfence.vma instruction
 * @vaddr: Virtual address to flush (0 for all)
 * @asid:  ASID to flush (0 for all)
 *
 * Flushes TLB entries. If both vaddr and asid are 0, performs
 * a global TLB flush.
 */
void vm_sfence_vma(uintptr_t vaddr, uintptr_t asid);

/**
 * vm_switch_mode - Switch to a different Sv mode
 * @ctx:      Page table context
 * @new_mode: New satp mode (SATP_MODE_SV39/SV48/SV57)
 *
 * Disables VM, reinitializes the page table for the new mode,
 * and rebuilds the identity mapping.
 */
void vm_switch_mode(pt_context_t *ctx, int new_mode);

/* ===================================================================
 * High-level Execution API
 * =================================================================== */

/**
 * vm_run_in_smode - Execute a function in S-mode with VM enabled
 * @ctx: Page table context (must have identity mapping set up)
 * @fn:  Function to execute in S-mode
 * @arg: Argument to pass to fn
 *
 * Sets up trap delegation, enables virtual memory, switches to
 * S-mode to execute fn(arg), then returns to M-mode with VM disabled.
 *
 * Returns the value returned by fn.
 */
uintptr_t vm_run_in_smode(pt_context_t *ctx,
                           uintptr_t (*fn)(uintptr_t),
                           uintptr_t arg);

/**
 * vm_run_in_umode - Execute a function in U-mode with VM enabled
 * @ctx: Page table context (must have identity mapping set up)
 * @fn:  Function to execute in U-mode
 * @arg: Argument to pass to fn
 *
 * Similar to vm_run_in_smode but targets U-mode. The caller must
 * ensure PTE.U=1 for all pages accessed by fn. Uses mret to jump
 * directly from M-mode to U-mode (MPP=0). The function returns to
 * M-mode via ecall (CAUSE_ECALL_FROM_U, cause 8).
 *
 * Returns the value returned by fn.
 */
uintptr_t vm_run_in_umode(pt_context_t *ctx,
                           uintptr_t (*fn)(uintptr_t),
                           uintptr_t arg);

/* ===================================================================
 * Page Table Inspection API
 * =================================================================== */

/**
 * pt_dump - Print page table entries for debugging
 * @ctx: Page table context
 *
 * Walks and prints all valid PTEs in the page table hierarchy.
 */
void pt_dump(pt_context_t *ctx);

/**
 * pt_get_pte - Get pointer to a PTE at a specific level
 * @ctx:   Page table context
 * @va:    Virtual address
 * @level: Target page table level (PT_LEVEL_4K / PT_LEVEL_2M / PT_LEVEL_1G)
 *
 * Walks the page table to the specified level and returns a pointer
 * to the PTE entry. Useful for manually modifying PTE fields like PBMT.
 *
 * Returns NULL if the PTE at the target level does not exist.
 */
uintptr_t *pt_get_pte(pt_context_t *ctx, uintptr_t va, int level);

/**
 * pte_read - Read the PTE value for VA at the given level
 *
 * Thin wrapper over pt_get_pte(): returns the PTE value, or 0 if the
 * PTE at the target level does not exist.
 */
uintptr_t pte_read(pt_context_t *ctx, uintptr_t va, int level);

/**
 * pte_set_bits - OR additional bits into the PTE for VA at the given
 * level, then issue an SFENCE.VMA to flush stale TLB entries.
 *
 * No-op if the PTE at the target level does not exist.
 */
void pte_set_bits(pt_context_t *ctx, uintptr_t va, int level,
                  uintptr_t bits);

/**
 * pte_clear_bits - AND the complement of @bits out of the PTE for VA at
 * the given level, then issue an SFENCE.VMA to flush stale TLB entries.
 *
 * No-op if the PTE at the target level does not exist.
 */
void pte_clear_bits(pt_context_t *ctx, uintptr_t va, int level,
                    uintptr_t bits);

/**
 * pte_write - Overwrite the PTE for VA at the given level with @value,
 * then issue an SFENCE.VMA to flush stale TLB entries.
 *
 * No-op if the PTE at the target level does not exist.
 */
void pte_write(pt_context_t *ctx, uintptr_t va, int level,
               uintptr_t value);

/**
 * vm_fill_exec_page - Fill a 4 KiB page with a nop sled ending in ret
 * @addr: Start address of the page (must be writable in the current
 *        address space; typically the .vm_test_region exec page)
 *
 * Writes 1023 nop (addi x0,x0,0) words followed by a single ret
 * (jalr x0,ra,0) at word 1023, so that a fetch landing anywhere in
 * the page slides to the ret. This is the authoritative version of the
 * per-suite init_exec_page()/init_exec_page_at() helper.
 */
void vm_fill_exec_page(uintptr_t addr);

/**
 * vm_setup_code_mapping - Identity-map the code/stack/page-table region
 * @ctx:       Page table context
 * @page_size: Mapping granularity (PAGE_SIZE_2M; PAGE_SIZE_4M for Sv32/RV32)
 * @regions:   Array of test-region start addresses (linker symbols) whose
 *             containing @page_size-aligned block must NOT be mapped, so that
 *             individual tests can install their own mappings there
 * @n_regions: Number of entries in @regions (0..N)
 *
 * Maps VA=PA identity pages over [PLATFORM_MEM_BASE, end) where
 * end = max(region aligned down to @page_size) + 2*@page_size, skipping the
 * aligned block of every region, then maps the UART page for S-mode console
 * output. Returns 0 on success or the first pt_map_page() error.
 *
 * This is the authoritative, parameterized version of the per-suite
 * setup_code_mapping(); the caller resolves its own linker symbols (which may
 * be declared as scalar or array) and passes the raw addresses here.
 */
int vm_setup_code_mapping(pt_context_t *ctx, uintptr_t page_size,
                          const uintptr_t *regions, unsigned int n_regions);

/**
 * get_pt_page_addr - Get physical address of page table page at level
 *
 * Walks the page table from root to find the page table page that
 * contains the PTE for the given virtual address at the target level.
 *
 * @ctx:          Page table context
 * @va:           Virtual address to look up
 * @target_level: Page table level (0=L0 PT page, 1=L1 PT page, 2=root)
 *
 * Returns the physical address of the page table page, or 0 on error.
 */
uintptr_t get_pt_page_addr(pt_context_t *ctx, uintptr_t va, int target_level);

#endif /* VM_H */
