/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef PM_ADDR_H
#define PM_ADDR_H

/* ===================================================================
 * Pointer Masking Address Utilities
 *
 * Pure inline functions for constructing, extracting, and verifying
 * tagged addresses used in Pointer Masking (PM) tests.
 *
 * Key concepts:
 *   - PMLEN: number of upper bits ignored by PM (7 or 16 on RV64)
 *   - Tag: value stored in the upper PMLEN bits of an address
 *   - Ignore transformation:
 *     * Virtual address: sign-extend from bit (XLEN-PMLEN-1)
 *     * Physical address: zero-extend (clear upper PMLEN bits)
 * =================================================================== */

#include "types.h"

/* ===================================================================
 * Tag embedding / extraction
 * =================================================================== */

/**
 * pm_tag_address - Embed a tag into the upper PMLEN bits of an address
 *
 * @addr:  base address (lower XLEN-PMLEN bits are preserved)
 * @tag:   tag value (only lower PMLEN bits are used)
 * @pmlen: number of masked bits (7 or 16)
 *
 * Returns: address with tag embedded in bits [XLEN-1 : XLEN-PMLEN]
 */
static inline uintptr_t pm_tag_address(uintptr_t addr, uintptr_t tag,
                                       unsigned pmlen) {
    unsigned xlen = sizeof(uintptr_t) * 8;
    uintptr_t tag_mask = ((1ULL << pmlen) - 1) << (xlen - pmlen);
    uintptr_t shifted_tag = (tag & ((1ULL << pmlen) - 1)) << (xlen - pmlen);
    return (addr & ~tag_mask) | shifted_tag;
}

/**
 * pm_extract_tag - Extract the tag from the upper PMLEN bits
 *
 * @addr:  tagged address
 * @pmlen: number of masked bits
 *
 * Returns: tag value (lower PMLEN bits significant)
 */
static inline uintptr_t pm_extract_tag(uintptr_t addr, unsigned pmlen) {
    unsigned xlen = sizeof(uintptr_t) * 8;
    return (addr >> (xlen - pmlen)) & ((1ULL << pmlen) - 1);
}

/* ===================================================================
 * Ignore transformation
 * =================================================================== */

/**
 * pm_transform_va - Apply the "ignore" transformation for virtual addresses
 *
 * Replaces upper PMLEN bits with sign-extension of bit (XLEN-PMLEN-1).
 * Equivalent to the Verilog:
 *   {{PMLEN{ea[XLEN-PMLEN-1]}}, ea[XLEN-PMLEN-1:0]}
 *
 * @addr:  effective address (possibly tagged)
 * @pmlen: number of masked bits
 *
 * Returns: transformed effective address
 */
static inline uintptr_t pm_transform_va(uintptr_t addr, unsigned pmlen) {
    /* Shift left to position bit (XLEN-PMLEN-1) at MSB, then
     * arithmetic right shift to sign-extend */
    intptr_t shifted = (intptr_t)(addr << pmlen);
    shifted >>= pmlen;
    return (uintptr_t)shifted;
}

/**
 * pm_transform_pa - Apply the "ignore" transformation for physical addresses
 *
 * Replaces upper PMLEN bits with 0 (zero-extension).
 * Equivalent to the Verilog:
 *   {{PMLEN{0}}, ea[XLEN-PMLEN-1:0]}
 *
 * @addr:  effective address (possibly tagged)
 * @pmlen: number of masked bits
 *
 * Returns: transformed effective address
 */
static inline uintptr_t pm_transform_pa(uintptr_t addr, unsigned pmlen) {
    unsigned xlen = sizeof(uintptr_t) * 8;
    if (pmlen >= xlen)
        return 0;
    uintptr_t mask = (1ULL << (xlen - pmlen)) - 1;
    return addr & mask;
}

/* ===================================================================
 * Equivalence checks
 * =================================================================== */

/**
 * pm_addrs_equivalent_va - Check if two addresses map to the same
 *                          location under VA pointer masking
 */
static inline bool pm_addrs_equivalent_va(uintptr_t a, uintptr_t b,
                                          unsigned pmlen) {
    return pm_transform_va(a, pmlen) == pm_transform_va(b, pmlen);
}

/**
 * pm_addrs_equivalent_pa - Check if two addresses map to the same
 *                          location under PA pointer masking
 */
static inline bool pm_addrs_equivalent_pa(uintptr_t a, uintptr_t b,
                                          unsigned pmlen) {
    return pm_transform_pa(a, pmlen) == pm_transform_pa(b, pmlen);
}

/* ===================================================================
 * Convenience: common tag patterns for testing
 * =================================================================== */

/* All-ones tag (maximum tag value for given PMLEN) */
static inline uintptr_t pm_max_tag(unsigned pmlen) {
    return (1ULL << pmlen) - 1;
}

/* Alternating bits tag: 0xAA... pattern truncated to PMLEN bits */
static inline uintptr_t pm_alt_tag(unsigned pmlen) {
    return 0xAAAAAAAAAAAAAAAAULL >> (64 - pmlen);
}

#endif /* PM_ADDR_H */
