/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * common/hyp/hyp_trap.c — HS-mode trap handler implementation
 *
 * Provides hs_trap_handler() for use when stvec points to
 * _hs_trap_entry (hyp_trap_asm.S). This handles traps delegated
 * from VS/VU-mode to HS-mode via hedeleg.
 *
 * The primary guest-page-fault capture (mtval2/mtinst/GVA) for the
 * M-mode path is still handled in common/trap.c (ENABLE_HYP).
 * This file handles the HS-mode path for hedeleg-delegated traps.
 * =================================================================== */

#include "hyp_trap.h"
#include "hyp_csr.h"
#include "encoding.h"

/* Provided by common/string.c (bare-metal libc replacement). */
extern void *memset(void *dst, int c, size_t n);

/* ===================================================================
 * HS-mode trap record (captures hypervisor-specific trap info)
 * =================================================================== */

static hyp_trap_record_t _hs_trap_record;

/* ===================================================================
 * Helper: determine instruction length from the first 2 bytes
 * =================================================================== */
static inline uintptr_t hs_next_instruction(uintptr_t epc) {
    /* Compressed instructions have bits [1:0] != 0b11 */
    uint16_t inst_lo = *(volatile uint16_t *)epc;
    return epc + ((inst_lo & 0x3) == 0x3 ? 4 : 2);
}

/* ===================================================================
 * hs_trap_handler — called from hyp_trap_asm.S
 *
 * Reads scause/sepc/stval (which in HS-mode refer to the HS-level
 * CSRs) plus hstatus.SPV/GVA and htval/htinst.
 *
 * Also acts as the S-level T-SBI service point while it is installed:
 * see the stage calls at the top of the body.
 *
 * @frame: the x1-x31 trap frame built by SAVE_CONTEXT.  The T-SBI opcode
 *         arrives in frame[TSBI_FRAME_A0] and any result must be written
 *         back there - RESTORE_CONTEXT reloads a0 from that slot, so the C
 *         return value never reaches the requester.
 *
 * Returns the privilege level for sret (unused by current asm, but
 * kept for future flexibility).
 * =================================================================== */

unsigned hs_trap_handler(uintptr_t *frame) {
    uintptr_t cause, epc, tval;
    cause = CSRR(scause);
    epc   = CSRR(sepc);
    tval  = CSRR(stval);

    /* ================================================================
     * T-SBI service stages - MUST precede the trap record below
     *
     * Tests install _hs_trap_entry into stvec *in place of* s_trap_entry, so
     * for as long as it is installed this function is the only S-level
     * service point that exists.  Skipping these stages would not merely
     * leave a VS-mode ecall unserved (the old code just advanced sepc past
     * it): it would take the whole S/HS-level protocol offline for the
     * duration of the test - CSR proxying included.
     *
     * HS is the S privilege level with V=0, so the served/forwarded split is
     * identical and the implementation is shared with s_trap_handler; see
     * tsbi.h SECTION 9b.
     *
     * They run before _hs_trap_record is written on purpose: a request we
     * served is framework traffic, not an observable event, and letting it
     * reach the record would corrupt hs_trap_was_triggered() for the test
     * that is actually watching.
     * ================================================================ */
    if (tsbi_s_proxy_capture(cause))
        return PRIV_S;

    if (!tsbi_raw_ecall_consume(cause) && tsbi_s_dispatch(frame, cause, epc))
        return PRIV_S;

    /* Read hypervisor-extension trap info */
    uintptr_t hstat  = hstatus_read();
    uintptr_t htval_v   = CSRR(CSR_HTVAL);
    uintptr_t htinst_v  = CSRR(CSR_HTINST);

    bool spv = (hstat & HSTATUS_SPV) ? true : false;
    bool gva = (hstat & HSTATUS_GVA) ? true : false;

    /* Record trap info */
    _hs_trap_record.triggered  = true;
    _hs_trap_record.cause      = cause;
    _hs_trap_record.epc        = epc;
    _hs_trap_record.tval       = tval;
    _hs_trap_record.htval      = htval_v;
    _hs_trap_record.htinst     = htinst_v;
    _hs_trap_record.gva        = gva;
    _hs_trap_record.spv        = spv;

    /* Interrupts: do NOT advance sepc — the interrupted instruction
     * must be re-executed after sret.  Clear only the hvip bit of the
     * interrupt that fired so other pending virtual interrupts (e.g.
     * VSTIP pending alongside VSSIP) remain deliverable. */
    if (cause & CAUSE_INTERRUPT_BIT) {
        uintptr_t irq = cause & ~CAUSE_INTERRUPT_BIT;
        CSRC(CSR_HVIP, 1UL << irq);
        return PRIV_S;
    }

    /* Handle specific trap causes */
    uintptr_t cause_code = cause & ~CAUSE_INTERRUPT_BIT; /* mask interrupt bit */

    switch (cause_code) {
    case CAUSE_ECALL_FROM_VS:
        /* A VS-mode ecall that survived the T-SBI dispatch above: either an
         * armed raw stimulus or an opcode nobody recognises.  Record it (done
         * already) and step over the ecall so the guest makes progress. */
        CSRW(sepc, epc + 4);
        break;

    case CAUSE_VIRTUAL_INSTRUCTION:
        /* Virtual-instruction exception — skip the faulting instruction */
        CSRW(sepc, hs_next_instruction(epc));
        break;

    case CAUSE_INST_GUEST_PAGE_FAULT:
    case CAUSE_LOAD_GUEST_PAGE_FAULT:
    case CAUSE_STORE_GUEST_PAGE_FAULT:
        /* Guest-page fault — skip the faulting instruction.
         * htval contains the faulting GPA >> 2. */
        CSRW(sepc, hs_next_instruction(epc));
        break;

    default:
        /* For other traps, just advance past the instruction */
        CSRW(sepc, hs_next_instruction(epc));
        break;
    }

    /* CFI (Zicfilp) test hook: force SPELP=1 before sret so tests
     * can verify hardware clears xpelp on sret (LP-17).
     * No-op unless g_trap_force_pelp is set by the test.
     * Use sstatus (not mstatus) because this is the HS-mode handler. */
#if __riscv_xlen > 32
    if (g_trap_force_pelp) {
        CSRS(sstatus, MSTATUS_SPELP_BIT);
    }
#endif

    /* Return to whatever mode was interrupted (sret uses sstatus.SPP
     * and hstatus.SPV to determine the target). */
    return PRIV_S; /* nominal S = HS-mode handler level */
}

/* ===================================================================
 * Merged accessors: HS-mode record first, M-mode snapshot second
 *
 * A trap reaches exactly one of the two records - hedeleg decides which -
 * and the test that set hedeleg has no reason to care.  So each accessor
 * answers from whichever record actually caught the trap.
 *
 * Both records are cleared together by trap_clear_record(), so "triggered"
 * cannot be a leftover from an earlier test.
 * =================================================================== */

bool trap_get_spv(void) {
    if (_hs_trap_record.triggered)
        return _hs_trap_record.spv;
    return trap_get_spv_snap();
}

uintptr_t trap_get_htval(void) {
    if (_hs_trap_record.triggered)
        return _hs_trap_record.htval;
    return trap_get_htval_snap();
}

uintptr_t trap_get_htinst(void) {
    if (_hs_trap_record.triggered)
        return _hs_trap_record.htinst;
    return trap_get_htinst_snap();
}

bool trap_get_gva(void) {
    if (_hs_trap_record.triggered)
        return _hs_trap_record.gva;
    return trap_get_gva_snap();
}

/* ===================================================================
 * Accessors for the HS-mode trap record
 *
 * These allow tests that install _hs_trap_entry as stvec to read
 * trap fields (cause, htinst, htval) captured by hs_trap_handler.
 * The cause/epc/tval trio is only available here - see the note in
 * test_framework.h for why it is not merged into trap_get_cause().
 * =================================================================== */

bool hs_trap_was_triggered(void) {
    return _hs_trap_record.triggered;
}

uintptr_t hs_trap_get_cause(void) {
    return _hs_trap_record.cause;
}

uintptr_t hs_trap_get_epc(void) {
    return _hs_trap_record.epc;
}

uintptr_t hs_trap_get_tval(void) {
    return _hs_trap_record.tval;
}

uintptr_t hs_trap_get_htinst(void) {
    return _hs_trap_record.htinst;
}

uintptr_t hs_trap_get_htval(void) {
    return _hs_trap_record.htval;
}

bool hs_trap_get_gva(void) {
    return _hs_trap_record.gva;
}

void hs_trap_record_reset(void) {
    /* Zero the entire record (including armed, priv_level and
     * return_addr) so no stale field survives a reset. */
    memset(&_hs_trap_record, 0, sizeof(_hs_trap_record));
}
