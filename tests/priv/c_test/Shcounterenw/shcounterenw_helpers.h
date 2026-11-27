/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef SHCOUNTERENW_HELPERS_H
#define SHCOUNTERENW_HELPERS_H

/*
 * shcounterenw_helpers.h - Shcounterenw Test Helpers
 *
 * Provides:
 *   - Counter implementation detection (wraps framework APIs)
 *   - Counter CSR address mapping
 *   - VS/VU-mode payload functions for counter reads
 *   - H-extension detection
 *
 * Uses framework APIs from common/hyp/hyp_csr.h exclusively.
 */

#include "test_framework.h"
#include "encoding.h"
#include "hyp/hyp_csr.h"
#include "hyp/hyp_priv.h"
#include "hyp/hyp_test.h"
#include "hyp/hyp_test_helpers.h"  /* vs_read_cycle, vs_read_time, vs_read_instret */

/* Dynamic CSR read/write (defined in common/csr_accessors.c) */
#include "csr_accessors.h"

/* ===================================================================
 * Counter index range constants
 * =================================================================== */
#define SHCNTW_FIRST_HPM  3
#define SHCNTW_LAST_HPM   31

/* ===================================================================
 * Counter CSR address by index (0=cycle, 1=time, 2=instret, 3-31=hpm)
 *
 * Returns the user-mode read-only CSR address for counter index i.
 * =================================================================== */
static inline uint16_t counter_csr_addr(unsigned i) {
    switch (i) {
    case 0:  return CSR_CYCLE;
    case 1:  return CSR_TIME;
    case 2:  return CSR_INSTRET;
    default: return (uint16_t)(CSR_HPMCOUNTER3 + (i - 3));
    }
}

/* ===================================================================
 * Counter implementation detection
 *
 * For i=0 (cycle), i=1 (time), i=2 (instret): assume implemented
 * (almost all platforms provide these).
 * For i=3..31: use framework's hpmcounter_is_writable() which probes
 * by writing mhpmcounter and reading back.
 * =================================================================== */
static inline bool is_counter_implemented(unsigned i) {
    if (i <= 2)
        return true;  /* cycle, time, instret assumed implemented */
    if (i > SHCNTW_LAST_HPM)
        return false;
    return hpmcounter_is_writable((int)i);
}

/* ===================================================================
 * Find the first implemented HPM counter (3-31).
 * Returns 0 if none found.
 * =================================================================== */
static inline unsigned find_first_hpm_counter(void) {
    for (unsigned n = SHCNTW_FIRST_HPM; n <= SHCNTW_LAST_HPM; n++) {
        if (is_counter_implemented(n))
            return n;
    }
    return 0;
}

/* ===================================================================
 * Find the first implemented HPM counter whose mcounteren gate bit
 * is WARL-writable (write-1 then readback sticks).
 *
 * Counter existence and mcounteren bit writability are independent:
 * norm:mcounteren_flds_rdonly0 permits read-only-zero gate bits even
 * for implemented counters (the counter is then permanently
 * inaccessible from lower privilege modes, and VS-mode reads legally
 * report illegal-instruction). Tests that need mcounteren[N]=1 as a
 * precondition must use this selector and TEST_SKIP when it returns
 * 0 ("gate-open" scenario not constructible on the platform).
 *
 * Returns 0 if no such counter exists.
 * =================================================================== */
static inline unsigned find_first_hpm_counter_gatable(void) {
    for (unsigned n = SHCNTW_FIRST_HPM; n <= SHCNTW_LAST_HPM; n++) {
        if (!is_counter_implemented(n))
            continue;
        uintptr_t bit = 1UL << n;
        uintptr_t saved = tsbi_csr_read(CSR_MCOUNTEREN);
        tsbi_csr_set(CSR_MCOUNTEREN, bit);
        bool sticky = (tsbi_csr_read(CSR_MCOUNTEREN) & bit) != 0;
        tsbi_csr_write(CSR_MCOUNTEREN, saved);
        if (sticky)
            return n;
    }
    return 0;
}

/* ===================================================================
 * VS-mode payload functions for counter reads
 *
 * vs_read_cycle, vs_read_time, vs_read_instret are provided by
 * common/hyp/hyp_test_helpers.c (identical semantics).
 * =================================================================== */

/* Generic VS-mode counter read using dynamic CSR accessor.
 * arg = CSR address (e.g., CSR_HPMCOUNTER3). */
static uintptr_t vsmode_read_counter(uintptr_t arg) {
    return csr_read((uint16_t)arg);
}

#endif /* SHCOUNTERENW_HELPERS_H */
