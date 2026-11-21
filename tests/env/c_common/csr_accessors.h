/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 *
 * csr_accessors.h - runtime-address CSR access (CSR number known only at runtime)
 *
 * RISC-V CSR instructions encode the register number as a compile-time
 * immediate, so csr_accessors.c maps each supported runtime address to a fixed
 * csrr/csrw via a switch-case. Use these when the CSR number is a variable
 * (loops over a range, table-driven tests, generic WARL probes).
 *
 * There is NO adaptive wrapper: the caller states the path explicitly, so it
 * always knows which route an access takes. Three families, by increasing
 * authority demanded of the caller:
 *
 *   csr_read()/csr_write()           DIRECT - one csrr/csrw in the CURRENT
 *                                    privilege. Use when the caller can already
 *                                    reach the CSR (e.g. inside an M-mode
 *                                    excursion). An address absent from the
 *                                    switch table trips csr_table_miss(): it
 *                                    logs (LOG_E), then returns a sentinel
 *                                    (read) or drops the write -- not silent.
 *   tsbi_csr_read/write/set/clear()  PROXY - always route through the T-SBI CSR
 *                                    handler (defined in tsbi/tsbi.h). Use from
 *                                    S(HS)-mode for M-level CSRs you cannot reach
 *                                    directly. Guarded: refuses trap-state CSRs
 *                                    and mstatus/sstatus return-path bits.
 *   mcsr_write()/mcsr_write_readback()  M-EXCURSION - run the access inside one
 *                                    run_in_priv(PRIV_M) excursion, for the
 *                                    trap-state CSRs the proxy refuses.
 *
 * For a fixed, known CSR prefer the named accessors in csr_ops.h (single
 * instruction, no dispatch, no coverage gap).
 */

#ifndef COMMON_CSR_ACCESSORS_H
#define COMMON_CSR_ACCESSORS_H

#include <stdbool.h>
#include "types.h"
#include "encoding.h"      /* PRIV_*, CSR_MSTATUS/SSTATUS, MSTATUS_* */
#include "tsbi/tsbi.h"     /* tsbi_csr_* proxy primitives + guard, tsbi_csr_is_* */

/* Direct runtime-number dispatcher (csr_accessors.c): one csrr/csrw in the
 * CURRENT privilege. An address absent from the switch table trips
 * csr_table_miss() (LOG_E): read returns the TSBI_RESERVED_RET sentinel, write
 * is dropped -- not a silent no-op. */
uintptr_t csr_read(uint16_t csr);
void      csr_write(uint16_t csr, uintptr_t val);

/* Bit set/clear by read-modify-write, symmetric with tsbi_csr_set/clear (the
 * proxied form). Two dispatches, so NOT a single-instruction csrs/csrc and not
 * atomic -- acceptable because no trap handler does RMW on a shared CSR and
 * tests are single-threaded (the 100+ asm csrs/csrc sites migrated to this
 * form regress identically). On a read-only CSR (absent from the write table)
 * csr_write only logs via csr_table_miss and emits no csrw, so a write-to-RO
 * trap stimulus must still use bare asm. */
static inline void csr_set(uint16_t csr, uintptr_t mask)
{
    csr_write(csr, csr_read(csr) | mask);
}

static inline void csr_clear(uint16_t csr, uintptr_t mask)
{
    csr_write(csr, csr_read(csr) & ~mask);
}

/* Current privilege tracker (privilege.c). Declared here so this header stays
 * self-contained and a lower layer than test_framework.h -- including that
 * here would invert the dependency. */
extern unsigned get_current_priv(void);

/* M-excursion accessors for trap-state / M-level CSRs that the tsbi_csr_*
 * proxy refuses (see tsbi_csr_is_trap_state() and the guard in tsbi/tsbi.h).
 * The whole access runs inside one run_in_priv(PRIV_M) excursion, so a
 * write-then-read-back has no intervening trap to clobber it. Implemented in
 * csr_accessors.c. */
extern void      mcsr_write(uint16_t csr, uintptr_t val);
extern uintptr_t mcsr_write_readback(uint16_t csr, uintptr_t val);

#endif /* COMMON_CSR_ACCESSORS_H */
