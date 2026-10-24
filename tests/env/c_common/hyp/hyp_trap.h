/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef HYP_TRAP_H
#define HYP_TRAP_H

/* ===================================================================
 * Hypervisor trap helpers
 *
 * The bulk of guest-page-fault capture logic lives in common/trap.c
 * (under #ifdef ENABLE_HYP), which records mtval2 / mtinst /
 * hstatus.GVA into the trap_record so that the existing
 * trap_get_*() accessors work uniformly.
 *
 * This header additionally provides:
 * - hyp_trap_record_t: extended trap record with hypervisor fields
 * - hs_trap_handler: HS-mode trap handler for hedeleg-delegated traps
 * - trap_get_spv: query whether trap came from V=1
 *
 * LIMITATION: The HS-mode trap handler (hs_trap_handler) records
 * trap information into a SEPARATE _hs_trap_record, which is
 * distinct from the M-mode trap record in common/trap.c.
 *
 * The hypervisor-specific accessors bridge the two: trap_get_spv(),
 * trap_get_htval(), trap_get_htinst() and trap_get_gva() answer from
 * whichever record caught the trap, so CHECK_HTVAL / CHECK_HTINST /
 * CHECK_GVA are valid under hedeleg delegation as well as with hedeleg=0.
 *
 * What does NOT bridge is the generic trio - trap_get_cause(),
 * trap_get_epc() and trap_get_tval() - together with
 * trap_was_triggered().  Those are half of the armed/triggered handshake
 * behind EXPECT_TRAP, and hs_trap_handler records unconditionally with no
 * armed check of its own, so merging them would let an HS-mode trap satisfy
 * an EXPECT_TRAP that was watching for an M-mode one.  A test watching a
 * delegated trap reads hs_trap_get_cause() / _epc() / _tval() below.
 * =================================================================== */

#include "types.h"
#include "encoding.h"
#include "test_framework.h"  /* trap_get_htval / htinst / gva */

/* ===================================================================
 * Extended trap record for hypervisor traps
 *
 * Extends the base trap_record with fields specific to H-extension
 * traps (htval, htinst, GVA, SPV).
 * =================================================================== */

typedef struct {
    /* Base trap record fields */
    bool      armed;
    bool      triggered;
    unsigned  priv_level;    /* privilege level at trap entry */
    uintptr_t cause;         /* scause (HS-mode) or mcause (M-mode) */
    uintptr_t epc;           /* sepc / mepc */
    uintptr_t tval;          /* stval / mtval */
    uintptr_t return_addr;

    /* Hypervisor extension fields */
    uintptr_t htval;         /* guest physical address >> 2 */
    uintptr_t htinst;        /* transformed instruction / pseudoinstruction */
    bool      gva;           /* hstatus.GVA: stval is guest virtual address */
    bool      spv;           /* hstatus.SPV: trap came from V=1 */
} hyp_trap_record_t;

/* ===================================================================
 * Direct CSR readers
 * =================================================================== */

/* Read mtval2 directly (faulting GPA >> 2 for guest-page-faults,
 * 0 otherwise). Use trap_get_htval() in tests instead of calling
 * this from a trap-recovery context. */
static inline uintptr_t mtval2_read(void) {
    return CSRR(CSR_MTVAL2);
}

/* Read mtinst directly. */
static inline uintptr_t mtinst_read(void) {
    return CSRR(CSR_MTINST);
}

/* ===================================================================
 * HS-mode trap handler
 *
 * Called from hyp_trap_asm.S (_hs_trap_entry) when stvec points to
 * the HS-mode trap vector. Handles traps delegated via hedeleg from
 * VS/VU-mode to HS-mode:
 *   - VS-mode ecall (cause=10): T-SBI service request, else privilege switch
 *   - Virtual-instruction exception (cause=22)
 *   - Guest-page fault (cause=20/21/23)
 *
 * While this vector is installed it REPLACES s_trap_entry, so it is also the
 * only S-level T-SBI service point in existence for the duration; it runs
 * the shared service stages (tsbi.h SECTION 9b) before recording anything.
 * =================================================================== */

/**
 * hs_trap_handler - HS-mode C trap handler
 *
 * @frame: x1-x31 trap frame built by SAVE_CONTEXT (common/trap_context.h);
 *         carries the T-SBI opcode in frame[TSBI_FRAME_A0] and takes the
 *         service result back in the same slot.
 *
 * Returns the privilege level to resume at after sret.
 */
unsigned hs_trap_handler(uintptr_t *frame);

/**
 * trap_get_spv - Get hstatus.SPV captured at last trap
 *
 * Returns true if the last trap originated from V=1 (VS/VU-mode).
 * Reads the HS-mode record when the trap landed there, the M-mode
 * snapshot otherwise.
 */
bool trap_get_spv(void);

/**
 * HS-mode trap record accessors
 *
 * Tests that install _hs_trap_entry as stvec can use these to read
 * trap fields captured by hs_trap_handler.  Unlike trap_get_htval() and
 * friends these never fall back to the M-mode record, so they say
 * specifically what the HS handler saw - which is what a test verifying
 * hedeleg delegation wants to assert on.
 */
bool hs_trap_was_triggered(void);
uintptr_t hs_trap_get_cause(void);
uintptr_t hs_trap_get_epc(void);
uintptr_t hs_trap_get_tval(void);
uintptr_t hs_trap_get_htinst(void);
uintptr_t hs_trap_get_htval(void);
bool hs_trap_get_gva(void);

/**
 * hs_trap_record_reset - Zero the HS-mode trap record
 *
 * Called by trap_clear_record() under ENABLE_HYP, so every reset_state()
 * clears this record along with the M-mode one.  Still exposed because a
 * test may want a clean slate mid-case, between arming and the stimulus.
 */
void hs_trap_record_reset(void);

/* External reference to the HS-mode trap vector entry point (asm) */
extern void _hs_trap_entry(void);

#endif /* HYP_TRAP_H */
