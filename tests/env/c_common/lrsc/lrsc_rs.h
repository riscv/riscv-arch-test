/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * lrsc_rs.h - shared reservation-set size bound derivation
 *
 * SPEC/riscv-isa-manual/src/unpriv/zars.adoc bounds the reservation
 * sets registered by the Zalrsc instructions:
 *
 *   norm:za128rs_res_set_req - contiguous, naturally aligned, <= 128 B
 *   norm:za64rs_res_set_req  - contiguous, naturally aligned, <= 64 B
 *   norm:za64rs_implies_za128rs - Za64rs implies Za128rs
 *
 * Without either declaration norm:lr_reservation_set_size
 * (zalrsc.adoc) lets an implementation register an arbitrarily large
 * reservation set, so the bound is 0 here and every "outside the
 * block" expectation becomes recording-only.
 *
 * This header is the SINGLE SOURCE OF TRUTH for the bound derivation
 * and the block predicates. The Zalrsc, Za128rs and Za64rs suites all
 * include it so that the same address is classified identically by
 * every suite (DOCS/testplan/Za64rs_test_plan.md implementation notes
 * 1 and 8: the cross-plan consistency assertions depend on it).
 *
 * ===================================================================
 * Geometry used by the predicates
 * ===================================================================
 * A reservation set S is a contiguous byte range [base, base + size).
 * "Naturally aligned" means base is a multiple of size, and size is a
 * power of two - the standard RISC-V reading of natural alignment
 * (zalrsc.adoc / zaamo.adoc use it for operand sizes), the granularity
 * hardware tracks reservations at, and the value the rva22.adoc NOTE
 * ties the bound to ("reduced to match the required cache block
 * size").
 *
 * With size <= n, size a power of two dividing n and base a multiple
 * of size, S lies entirely inside the naturally aligned n-byte block
 * that holds any of its members:
 *
 *   x in S  =>  S subset of block(x, n)
 *
 * Two consequences drive every hard assertion in the Zars suites:
 *
 *   Lemma 1 (block containment): if a and b lie in different n-byte
 *     blocks then no compliant S contains both, so an SC to b after an
 *     LR to a must fail (norm:sc_addr_not_in_reservation_fail). Note S
 *     lies inside block(x, n) for EVERY x in S, so a does not have to be
 *     n-aligned for this.
 *   Lemma 2 (crossing exclusion): the special case b >= a with
 *     (b mod n) < (a mod n), where the two addresses straddle a block
 *     boundary at unequal offsets - this is what rules out a sliding
 *     window and so verifies the natural-alignment property. For
 *     b = a +- n the residues are EQUAL while the blocks still differ,
 *     so the general criterion is "different blocks", never a residue
 *     comparison.
 *
 * Both reduce to one predicate: "a and b are in different n-byte
 * blocks" (lrsc_rs_diff_block below).
 *
 * Lemma 3 (implication): a 64-byte block is entirely inside one
 * 128-byte block, so the set of addresses that are outside block(a,64)
 * is a SUPERSET of those outside block(a,128). A platform declaring
 * Za64rs therefore satisfies every Za128rs obligation.
 *
 * Lemma 4 (VA/PA congruence): page-based translation maps pages of at
 * least 4 KiB and both the VA and the PA page bases are multiples of
 * 4 KiB. Since 64 | 128 | 4096, (va mod n) == (pa mod n) for every
 * mapped address, so block membership - and therefore every verdict
 * below - is identical before and after translation.
 * ===================================================================
 */

#ifndef COMMON_LRSC_RS_H
#define COMMON_LRSC_RS_H

#include "types.h"

/* ===================================================================
 * Declared bound (compile time, from config/<platform>/rvtest_config.h)
 *
 * Za64rs is the stricter bound and implies Za128rs, so it wins when
 * both are declared. 0 means "no bound declared".
 * =================================================================== */
#if defined(ZA64RS_SUPPORTED)
#define LRSC_RS_BOUND           64
#define LRSC_RS_BOUND_NAME      "Za64rs"
#elif defined(ZA128RS_SUPPORTED)
#define LRSC_RS_BOUND           128
#define LRSC_RS_BOUND_NAME      "Za128rs"
#else
#define LRSC_RS_BOUND           0
#define LRSC_RS_BOUND_NAME      "none"
#endif

/* The two architectural bounds, independent of what the platform
 * declares. Used by the implication cases, which have to evaluate both
 * readings on the same address set. */
#define LRSC_RS_ZA64RS_BOUND    64
#define LRSC_RS_ZA128RS_BOUND   128

#ifdef ZA64RS_SUPPORTED
#define LRSC_RS_ZA64RS_DECLARED     1
#else
#define LRSC_RS_ZA64RS_DECLARED     0
#endif

#ifdef ZA128RS_SUPPORTED
#define LRSC_RS_ZA128RS_DECLARED    1
#else
#define LRSC_RS_ZA128RS_DECLARED    0
#endif

/* Any bound declared at all (Za64rs or Za128rs). */
#define LRSC_RS_ANY_DECLARED \
    (LRSC_RS_ZA64RS_DECLARED || LRSC_RS_ZA128RS_DECLARED)

/* ===================================================================
 * Base physical page (priv/supervisor.adoc): with both page-based
 * virtual memory and the A extension the LR/SC reservation set must lie
 * completely within a single naturally aligned 4 KiB region. This bound
 * does NOT depend on a Zars declaration.
 * =================================================================== */
#define LRSC_RS_BASE_PAGE       4096

/* ===================================================================
 * Block predicates
 *
 * n must be a power of two. All of them are pure address arithmetic and
 * are safe to call from any privilege level.
 * =================================================================== */

/* Start of the naturally aligned n-byte block holding addr. */
static inline uintptr_t lrsc_rs_block_start(uintptr_t addr, uintptr_t n)
{
    return addr & ~(n - 1);
}

/* True when addr and other fall in the same naturally aligned n-byte
 * block. */
static inline bool lrsc_rs_same_block(uintptr_t addr, uintptr_t other,
                                      uintptr_t n)
{
    return lrsc_rs_block_start(addr, n) == lrsc_rs_block_start(other, n);
}

/* True when no compliant reservation set (contiguous, naturally
 * aligned, at most n bytes) can contain both addr and other - Lemma 1
 * and Lemma 2 combined. An SC to `other` after an LR to `addr` must
 * then fail (norm:sc_addr_not_in_reservation_fail). */
static inline bool lrsc_rs_diff_block(uintptr_t addr, uintptr_t other,
                                      uintptr_t n)
{
    return !lrsc_rs_same_block(addr, other, n);
}

/* True when addr and other lie in different 4 KiB base physical pages
 * (the supervisor.adoc baseline). */
static inline bool lrsc_rs_diff_base_page(uintptr_t addr, uintptr_t other)
{
    return lrsc_rs_diff_block(addr, other, (uintptr_t)LRSC_RS_BASE_PAGE);
}

/* True when `addr` is naturally aligned to n. */
static inline bool lrsc_rs_aligned(uintptr_t addr, uintptr_t n)
{
    return (addr & (n - 1)) == 0;
}

#endif /* COMMON_LRSC_RS_H */
