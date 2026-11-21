/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#include "pmp_cfg.h"
#include "encoding.h"
#include "uart.h"

/* Dynamic CSR access (defined in csr_accessors.c) */
extern uintptr_t csr_read(uint16_t csr);
extern void csr_write(uint16_t csr, uintptr_t val);

/* Trap API from trap.c */
extern void trap_expect_begin(void);
extern void trap_expect_end(void);
extern bool trap_was_triggered(void);

/* ===================================================================
 * Internal helpers
 * =================================================================== */

/**
 * Get the CSR address for pmpcfg register containing entry 'index'.
 *
 * RV64: pmpcfg0 (entries 0-7), pmpcfg2 (entries 8-15), ...
 *       Only even-numbered pmpcfg CSRs exist.
 * RV32: pmpcfg0 (entries 0-3), pmpcfg1 (entries 4-7), ...
 *       All pmpcfg CSRs exist.
 */
static uint16_t pmpcfg_csr_for_entry(unsigned int index) {
#if __riscv_xlen == 64
    /* 8 entries per CSR, only even CSR numbers */
    return CSR_PMPCFG0 + (index / 8) * 2;
#else
    /* 4 entries per CSR */
    return CSR_PMPCFG0 + (index / 4);
#endif
}

/**
 * Get the byte offset within the pmpcfg CSR for entry 'index'.
 */
static unsigned int pmpcfg_byte_offset(unsigned int index) {
#if __riscv_xlen == 64
    return (index % 8);
#else
    return (index % 4);
#endif
}

/**
 * Get the CSR address for pmpaddr register of entry 'index'.
 */
static uint16_t pmpaddr_csr_for_entry(unsigned int index) {
    return CSR_PMPADDR0 + index;
}

/* ===================================================================
 * Address encoding
 * =================================================================== */

uintptr_t pmp_encode_napot(uintptr_t base, uint64_t size) {
    if (size == 0)
        return 0;

    /* Ensure size is power of 2 */
    if (size & (size - 1)) {
        uint64_t s = 1;
        while (s < size)
            s <<= 1;
        size = s;
    }

    /* Calculate log2(size) */
    unsigned int log2_size = 0;
    uint64_t tmp = size;
    while (tmp >>= 1)
        log2_size++;

    if (log2_size < 3)
        return base >> 2;  /* Fallback: treat as NA4 */

    /*
     * NAPOT encoding:
     *   pmpaddr = (base >> 2) | ((1 << (log2_size - 3)) - 1)
     *
     * The low (log2_size - 3) bits of pmpaddr are set to 1,
     * encoding the region size.
     */
    unsigned int L = log2_size - 3;
    uintptr_t base_shifted = base >> 2;
    uintptr_t low_ones = (L >= sizeof(uintptr_t) * 8) ?
                         (uintptr_t)-1 : (((uintptr_t)1 << L) - 1);

    return base_shifted | low_ones;
}

uintptr_t pmp_encode_tor(uintptr_t addr) {
    return addr >> 2;
}

uintptr_t pmp_encode_na4(uintptr_t addr) {
    return addr >> 2;
}

/* ===================================================================
 * Core API implementation
 * =================================================================== */

void pmp_set_entry(unsigned int index, const pmp_entry_t *entry) {
    if (index >= PMP_MAX_ENTRIES)
        return;

    uint16_t addr_csr = pmpaddr_csr_for_entry(index);
    uint16_t cfg_csr  = pmpcfg_csr_for_entry(index);
    unsigned int byte_off = pmpcfg_byte_offset(index);

    /* Encode and write pmpaddr */
    uintptr_t pmpaddr_val;
    uint8_t a_mode = PMP_CFG_A(entry->cfg);

    switch (a_mode) {
    case 0: /* OFF */
        /* Even in OFF mode, write the addr field if provided.
         * This is needed for TOR: entry[i-1] in OFF mode still provides
         * the lower bound for entry[i] in TOR mode via pmpaddr[i-1].
         * If addr == 0, write 0 (default). Otherwise write addr >> 2. */
        pmpaddr_val = (entry->addr != 0) ? (entry->addr >> 2) : 0;
        break;
    case 1: /* TOR */
        pmpaddr_val = pmp_encode_tor(entry->addr);
        break;
    case 2: /* NA4 */
        pmpaddr_val = pmp_encode_na4(entry->addr);
        break;
    case 3: /* NAPOT */
        pmpaddr_val = pmp_encode_napot(entry->addr, entry->size);
        break;
    default:
        pmpaddr_val = 0;
        break;
    }

    /* Write pmpaddr first (before enabling via pmpcfg) */
    csr_write(addr_csr, pmpaddr_val);

    /* Read-modify-write pmpcfg */
    uintptr_t cfg_val = csr_read(cfg_csr);
    unsigned int shift = byte_off * 8;
    uintptr_t mask = (uintptr_t)0xFF << shift;

    cfg_val &= ~mask;
    cfg_val |= ((uintptr_t)(entry->cfg) << shift);

    csr_write(cfg_csr, cfg_val);
}

void pmp_get_entry(unsigned int index, pmp_entry_t *entry) {
    if (index >= PMP_MAX_ENTRIES)
        return;

    uint16_t addr_csr = pmpaddr_csr_for_entry(index);
    uint16_t cfg_csr  = pmpcfg_csr_for_entry(index);
    unsigned int byte_off = pmpcfg_byte_offset(index);

    /* Read pmpcfg byte */
    uintptr_t cfg_val = csr_read(cfg_csr);
    unsigned int shift = byte_off * 8;
    entry->cfg = (uint8_t)((cfg_val >> shift) & 0xFF);

    /* Read pmpaddr and decode back to physical address */
    uintptr_t pmpaddr_val = csr_read(addr_csr);
    entry->addr = pmpaddr_val << 2;

    /* For NAPOT, decode size from pmpaddr low bits */
    uint8_t a_mode = PMP_CFG_A(entry->cfg);
    if (a_mode == 3) { /* NAPOT */
        /* Count trailing ones in pmpaddr to determine size */
        uintptr_t trailing = pmpaddr_val;
        unsigned int count = 0;
        while (trailing & 1) {
            count++;
            trailing >>= 1;
        }
        entry->size = (uint64_t)1 << (count + 3);
        /* Reconstruct base address */
        entry->addr = (pmpaddr_val & ~(((uintptr_t)1 << count) - 1)) << 2;
    } else if (a_mode == 2) { /* NA4 */
        entry->size = 4;
    } else {
        entry->size = 0;
    }
}

void pmp_clear_entry(unsigned int index) {
    pmp_entry_t off = PMP_ENTRY_OFF();
    pmp_set_entry(index, &off);
}

/* Cached entry count (0 = not yet detected) */
static unsigned int _cached_entry_count = 0;

void pmp_clear_all(void) {
    /* Detect entry count once */
    if (_cached_entry_count == 0)
        _cached_entry_count = pmp_detect_entry_count();

    unsigned int count = _cached_entry_count;
    if (count == 0)
        return;

    /* Clear pmpcfg registers for implemented entries */
    unsigned int num_cfg_csrs;
#if __riscv_xlen == 64
    num_cfg_csrs = count / 8;  /* 8 entries per CSR on RV64 */
    for (unsigned int i = 0; i < num_cfg_csrs; i++)
        csr_write(CSR_PMPCFG0 + i * 2, 0);
#else
    num_cfg_csrs = count / 4;  /* 4 entries per CSR on RV32 */
    for (unsigned int i = 0; i < num_cfg_csrs; i++)
        csr_write(CSR_PMPCFG0 + i, 0);
#endif

    /* Clear pmpaddr registers for implemented entries */
    for (unsigned int i = 0; i < count; i++)
        csr_write(CSR_PMPADDR0 + i, 0);
}

void pmp_set_entries(const pmp_entry_t *entries, unsigned int count,
                     unsigned int start_index) {
    for (unsigned int i = 0; i < count; i++) {
        if (start_index + i >= PMP_MAX_ENTRIES)
            break;
        pmp_set_entry(start_index + i, &entries[i]);
    }
}

/* ===================================================================
 * Hardware capability detection
 * =================================================================== */

unsigned int pmp_detect_granularity(void) {
    /*
     * Algorithm from RISC-V spec:
     * 1. Write 0 to pmp0cfg (set A=OFF)
     * 2. Write all-ones to pmpaddr0
     * 3. Read back pmpaddr0
     * 4. G = index of least-significant bit set
     * 5. Minimum region size = 2^(G+2)
     */

    /* Save current values */
    uintptr_t saved_cfg  = csr_read(CSR_PMPCFG0);
    uintptr_t saved_addr = csr_read(CSR_PMPADDR0);

    /* Set entry 0 to OFF mode */
    uintptr_t cfg_val = saved_cfg & ~(uintptr_t)0xFF;  /* Clear byte 0 */
    csr_write(CSR_PMPCFG0, cfg_val);

    /* Write all ones to pmpaddr0 */
    csr_write(CSR_PMPADDR0, (uintptr_t)-1);

    /* Read back */
    uintptr_t readback = csr_read(CSR_PMPADDR0);

    /* Restore */
    csr_write(CSR_PMPADDR0, saved_addr);
    csr_write(CSR_PMPCFG0, saved_cfg);

    /* Find G: index of least-significant bit set */
    if (readback == 0)
        return XLEN;  /* All bits masked: maximum granularity */

    unsigned int g = 0;
    while ((readback & 1) == 0) {
        g++;
        readback >>= 1;
    }

    return g;
}

unsigned int pmp_detect_entry_count(void) {
    /*
     * Try writing to pmpaddr registers and reading back.
     * Unimplemented entries read as 0 regardless of writes.
     */

    /* Save and test entry 0 (always implemented if any PMP exists) */
    uintptr_t saved = csr_read(CSR_PMPADDR0);
    csr_write(CSR_PMPADDR0, (uintptr_t)-1);
    uintptr_t val = csr_read(CSR_PMPADDR0);
    csr_write(CSR_PMPADDR0, saved);

    if (val == 0)
        return 0;  /* No PMP entries */

    /* Test entry 16 (may not exist, use trap arming) */
    trap_expect_begin();
    saved = csr_read(CSR_PMPADDR16);
    if (trap_was_triggered()) {
        trap_expect_end();
        return 16;
    }
    csr_write(CSR_PMPADDR16, (uintptr_t)-1);
    if (trap_was_triggered()) {
        trap_expect_end();
        return 16;
    }
    val = csr_read(CSR_PMPADDR16);
    csr_write(CSR_PMPADDR16, saved);
    trap_expect_end();

    if (val == 0)
        return 16;

    return 64;
}

/* ===================================================================
 * mseccfg Access API (Smepmp Extension)
 * =================================================================== */

uint64_t mseccfg_read(void) {
#if __riscv_xlen == 64
    return (uint64_t)csr_read(CSR_MSECCFG);
#else
    uint32_t lo = (uint32_t)csr_read(CSR_MSECCFG);
    uint32_t hi = (uint32_t)csr_read(CSR_MSECCFGH);
    return ((uint64_t)hi << 32) | lo;
#endif
}

void mseccfg_write(uint64_t val) {
#if __riscv_xlen == 64
    csr_write(CSR_MSECCFG, (uintptr_t)val);
#else
    csr_write(CSR_MSECCFG, (uintptr_t)(val & 0xFFFFFFFF));
    csr_write(CSR_MSECCFGH, (uintptr_t)(val >> 32));
#endif
}

void mseccfg_set(uint64_t bits) {
    uint64_t val = mseccfg_read();
    val |= bits;
    mseccfg_write(val);
}

void mseccfg_clear(uint64_t bits) {
    uint64_t val = mseccfg_read();
    val &= ~bits;
    mseccfg_write(val);
}

bool smepmp_is_supported(void) {
    /*
     * Try to read/write mseccfg.RLB (bit 2).
     * If Smepmp is not implemented, mseccfg does not exist and
     * accessing it causes an illegal instruction exception.
     */
    trap_expect_begin();
    uint64_t saved = mseccfg_read();
    if (trap_was_triggered()) {
        trap_expect_end();
        return false;
    }

    /* Try to set RLB */
    mseccfg_set(MSECCFG_RLB);
    if (trap_was_triggered()) {
        trap_expect_end();
        return false;
    }

    uint64_t val = mseccfg_read();
    if (trap_was_triggered()) {
        trap_expect_end();
        return false;
    }

    /* Restore */
    mseccfg_write(saved);
    trap_expect_end();

    return (val & MSECCFG_RLB) != 0;
}
