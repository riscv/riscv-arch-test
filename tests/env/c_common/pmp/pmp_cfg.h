/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef PMP_CFG_H
#define PMP_CFG_H

/* PMP permission/mode bit constants (PMP_R, PMP_W, PMP_X, PMP_A_*,
 * PMP_L, etc.) are defined in sm_defs.h, included via encoding.h. */
#include "encoding.h"

/* ===================================================================
 * PMP Configuration Field Extraction / Construction Helpers
 *
 * PMP entry config register layout:
 *   [7]   L   - Lock
 *   [6:5] 00  - Reserved (WARL, reads as 0)
 *   [4:3] A   - Address matching mode
 *   [2]   X   - Execute permission
 *   [1]   W   - Write permission
 *   [0]   R   - Read permission
 * =================================================================== */

/* Field extraction macros */
#define PMP_CFG_R(cfg)      ((cfg) & 0x1)
#define PMP_CFG_W(cfg)      (((cfg) >> 1) & 0x1)
#define PMP_CFG_X(cfg)      (((cfg) >> 2) & 0x1)
#define PMP_CFG_A(cfg)      (((cfg) >> 3) & 0x3)
#define PMP_CFG_L(cfg)      (((cfg) >> 7) & 0x1)

/* Field construction helpers */
#define PMP_CFG_A_SET(mode) (((mode) & 0x3) << 3)

/* Maximum PMP entries per spec */
#define PMP_MAX_ENTRIES     64

/* ===================================================================
 * PMP Entry Configuration Structure
 *
 * Users fill this structure and pass it to pmp_set_entry().
 * The framework handles the encoding details internally.
 * =================================================================== */
typedef struct {
    uint8_t   cfg;      /* pmpcfg value: L|00|A|X|W|R */
    uintptr_t addr;     /* Physical address (raw, not shifted) */
    uint64_t  size;     /* Region size in bytes (NAPOT mode only) */
} pmp_entry_t;

/* ===================================================================
 * Core API
 * =================================================================== */

/**
 * pmp_set_entry - Configure a single PMP entry
 *
 * @index: PMP entry index (0-63)
 * @entry: Configuration to apply
 *
 * Internally handles:
 *   - Address encoding (>> 2 for pmpaddr)
 *   - NAPOT size encoding
 *   - pmpcfg byte packing (4 entries per CSR on RV32, 8 on RV64)
 */
void pmp_set_entry(unsigned int index, const pmp_entry_t *entry);

/**
 * pmp_get_entry - Read current configuration of a PMP entry
 *
 * @index: PMP entry index (0-63)
 * @entry: Output structure (addr is decoded back to physical address)
 */
void pmp_get_entry(unsigned int index, pmp_entry_t *entry);

/**
 * pmp_clear_entry - Disable a single PMP entry (set A=OFF)
 */
void pmp_clear_entry(unsigned int index);

/**
 * pmp_clear_all - Disable all PMP entries
 */
void pmp_clear_all(void);

/**
 * pmp_set_entries - Configure multiple consecutive PMP entries
 *
 * @entries:     Array of configurations
 * @count:       Number of entries
 * @start_index: First PMP entry index
 */
void pmp_set_entries(const pmp_entry_t *entries, unsigned int count,
                     unsigned int start_index);

/* ===================================================================
 * Address Encoding Helpers
 * =================================================================== */

/**
 * pmp_encode_napot - Encode (base, size) for NAPOT mode pmpaddr
 *
 * @base: Region base address (must be naturally aligned to size)
 * @size: Region size (must be power of 2, >= 8 bytes)
 * @return: Value to write to pmpaddr register
 */
uintptr_t pmp_encode_napot(uintptr_t base, uint64_t size);

/**
 * pmp_encode_tor - Encode address for TOR mode pmpaddr
 *
 * @addr: Top of range address
 * @return: Value to write to pmpaddr register
 */
uintptr_t pmp_encode_tor(uintptr_t addr);

/**
 * pmp_encode_na4 - Encode address for NA4 mode pmpaddr
 *
 * @addr: 4-byte aligned address
 * @return: Value to write to pmpaddr register
 */
uintptr_t pmp_encode_na4(uintptr_t addr);

/* ===================================================================
 * Hardware Capability Detection
 * =================================================================== */

/**
 * pmp_detect_granularity - Detect PMP granularity G value
 *
 * @return: G value. Minimum region size = 2^(G+2) bytes.
 *          G=0 means 4-byte granularity (NA4 supported).
 */
unsigned int pmp_detect_granularity(void);

/**
 * pmp_detect_entry_count - Detect number of implemented PMP entries
 *
 * @return: 0, 16, or 64
 */
unsigned int pmp_detect_entry_count(void);

/* ===================================================================
 * mseccfg Access API (Smepmp Extension)
 * =================================================================== */

/**
 * mseccfg_read - Read the full mseccfg register
 *
 * On RV32, combines mseccfg and mseccfgh into a 64-bit value.
 */
uint64_t mseccfg_read(void);

/**
 * mseccfg_write - Write the full mseccfg register
 *
 * On RV32, splits into mseccfg (low 32) and mseccfgh (high 32).
 */
void mseccfg_write(uint64_t val);

/**
 * mseccfg_set - Set specific bits in mseccfg (OR operation)
 */
void mseccfg_set(uint64_t bits);

/**
 * mseccfg_clear - Clear specific bits in mseccfg (AND-NOT operation)
 *
 * Note: MML and MMWP are sticky bits - once set, they cannot be
 * cleared until PMP reset. Attempting to clear them will be ignored
 * by hardware.
 */
void mseccfg_clear(uint64_t bits);

/**
 * smepmp_is_supported - Detect if Smepmp extension is available
 *
 * Attempts to write and read back mseccfg.RLB to detect presence.
 * Returns true if Smepmp is supported.
 */
bool smepmp_is_supported(void);

/* ===================================================================
 * Convenience Construction Macros
 *
 * Usage:
 *   pmp_entry_t e = PMP_ENTRY_NAPOT(0x80000000, 0x1000, PMP_RWX);
 *   pmp_set_entry(0, &e);
 * =================================================================== */

#define PMP_ENTRY_NAPOT(base, sz, rwx_flags) \
    (pmp_entry_t){ .cfg = PMP_A_NAPOT | (rwx_flags), \
                   .addr = (base), .size = (sz) }

/* NAPOT entry covering the entire physical address space.
 * RV64: 2^56 bytes (full Sv39/Sv48/Sv57 physical address width).
 * RV32: 2^32 bytes (full 4 GiB address space). */
#if __riscv_xlen == 64
#define PMP_ENTRY_FULL(rwx_flags) \
    PMP_ENTRY_NAPOT(0x0, (1ULL << 56), (rwx_flags))
#else
#define PMP_ENTRY_FULL(rwx_flags) \
    PMP_ENTRY_NAPOT(0x0, 0x100000000ULL, (rwx_flags))
#endif

#define PMP_ENTRY_TOR(top_addr, rwx_flags) \
    (pmp_entry_t){ .cfg = PMP_A_TOR | (rwx_flags), \
                   .addr = (top_addr), .size = 0 }

#define PMP_ENTRY_NA4(address, rwx_flags) \
    (pmp_entry_t){ .cfg = PMP_A_NA4 | (rwx_flags), \
                   .addr = (address), .size = 4 }

#define PMP_ENTRY_OFF() \
    (pmp_entry_t){ .cfg = PMP_A_OFF, .addr = 0, .size = 0 }

/* Locked variants */
#define PMP_ENTRY_NAPOT_LOCKED(base, sz, rwx_flags) \
    (pmp_entry_t){ .cfg = PMP_L | PMP_A_NAPOT | (rwx_flags), \
                   .addr = (base), .size = (sz) }

#define PMP_ENTRY_TOR_LOCKED(top_addr, rwx_flags) \
    (pmp_entry_t){ .cfg = PMP_L | PMP_A_TOR | (rwx_flags), \
                   .addr = (top_addr), .size = 0 }

/* ===================================================================
 * PMP deny-window helpers
 *
 * Convenience API for the common test pattern: temporarily deny or
 * restrict access to a single 4KB page using PMP entries 0 and 1,
 * then restore the original configuration.
 *
 * Strategy:
 *   - Entry 0: NAPOT matching the target 4KB page (deny or restrict)
 *   - Entry 1: NAPOT covering all space with full RWX (fall-through)
 *   - Both entries unlocked (L=0) so M-mode is never affected.
 *
 * Callers that need TLB/PMP-cache synchronization should issue
 * appropriate fences (sfence.vma / hfence.gvma) after calling these.
 * =================================================================== */

typedef struct {
    pmp_entry_t e0;
    pmp_entry_t e1;
} pmp_save_t;

/* Deny a 4KB page completely (no R/W/X). */
static inline void pmp_deny_page_4k(uintptr_t pa, pmp_save_t *save) {
    pmp_get_entry(0, &save->e0);
    pmp_get_entry(1, &save->e1);
    pmp_entry_t deny = PMP_ENTRY_NAPOT(pa & ~0xfffUL, 0x1000UL, 0);
    pmp_set_entry(0, &deny);
    pmp_entry_t allow = PMP_ENTRY_NAPOT(0, (uintptr_t)1UL << 54, PMP_RWX);
    pmp_set_entry(1, &allow);
}

/* Grant execute-only on a 4KB page (X=1, R=0, W=0). */
static inline void pmp_xonly_page_4k(uintptr_t pa, pmp_save_t *save) {
    pmp_get_entry(0, &save->e0);
    pmp_get_entry(1, &save->e1);
    pmp_entry_t xonly = PMP_ENTRY_NAPOT(pa & ~0xfffUL, 0x1000UL, PMP_X);
    pmp_set_entry(0, &xonly);
    pmp_entry_t allow = PMP_ENTRY_NAPOT(0, (uintptr_t)1UL << 54, PMP_RWX);
    pmp_set_entry(1, &allow);
}

/* Restore PMP entries 0 and 1 from a saved state. */
static inline void pmp_restore(const pmp_save_t *save) {
    pmp_set_entry(0, &save->e0);
    pmp_set_entry(1, &save->e1);
}

/* Quick PMP entry-0 full-space NAPOT RWX open (for S/U-mode access).
 * Lightweight alternative to pmp_set_entry() when only a catch-all
 * permission grant is needed (no save/restore).
 *
 * PMP CSRs are M-level.  Under the S-mode-normal model the write must run
 * inside an M-excursion; run_in_priv() is a no-op when already in M-mode,
 * so M-boot callers are unaffected. */
extern uintptr_t run_in_priv(unsigned priv, uintptr_t (*fn)(uintptr_t), uintptr_t arg);

static inline uintptr_t _pmp_open_entry0_all_m(uintptr_t arg)
{
    (void)arg;
    asm volatile(
        "li t0, -1\n\t"
        "csrw pmpaddr0, t0\n\t"
        "li t0, 0x1F\n\t"
        "csrw pmpcfg0, t0\n\t"
        ::: "t0");
    return 0;
}

static inline void pmp_open_entry0_all(void)
{
    run_in_priv(PRIV_M, _pmp_open_entry0_all_m, 0);
}

/* Clear all PMP entries then open entry 0 as a full-space RWX NAPOT
 * region, so S-mode (and U-mode) accesses are permitted by PMP. This
 * is the authoritative version of the per-suite ensure_smode_pmp().
 *
 * The whole clear-and-reinstall sequence MUST run inside ONE M-excursion:
 * pmp_clear_all() leaves no matching entry, and the implicit no-match rule
 * denies every S/U access, so returning to S-mode before entry 0 is
 * re-opened would fault on the very next instruction fetch.  run_in_priv()
 * is a no-op when already in M-mode, so M-boot callers are unaffected. */
static inline uintptr_t _ensure_smode_pmp_m(uintptr_t arg)
{
    (void)arg;
    pmp_clear_all();
    pmp_entry_t pmp_all = PMP_ENTRY_FULL(PMP_RWX);
    pmp_set_entry(0, &pmp_all);
    return 0;
}

static inline void ensure_smode_pmp(void)
{
    run_in_priv(PRIV_M, _ensure_smode_pmp_m, 0);
}

#endif /* PMP_CFG_H */
