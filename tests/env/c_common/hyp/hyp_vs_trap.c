/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * common/hyp/hyp_vs_trap.c — VS-mode custom trap entry support
 * =================================================================== */

#include "hyp_vs_trap.h"
#include "hyp_csr.h"
#include "test_framework.h"

/* The framework VS entry in hyp_vs_trap_asm.S (installed by
 * vs_trap_setup_framework below). */
extern void _vs_trap_entry(void);

/* Internal VS trap record (singleton — one active test at a time) */
static vs_trap_record_t _vs_trap_record;

/* ===================================================================
 * VS trap handler configuration
 * =================================================================== */

void vs_trap_setup(vs_trap_config_t *cfg) {
    /* The vector base must be 4-byte aligned: VSTVEC_BASE_MASK discards
     * bits 1:0, so a 2-byte-aligned handler address would silently make
     * trap entry start 2 bytes BEFORE the handler (executing whatever
     * instruction precedes it). Fail visibly instead of mis-trapping. */
    if (cfg->handler_base & 0x3UL) {
        LOG_E("vs_trap_setup: handler 0x%lx not 4-byte aligned\n",
              (unsigned long)cfg->handler_base);
        while (1) {}
    }
    uintptr_t tvec_val = (cfg->handler_base & VSTVEC_BASE_MASK) |
                         ((uintptr_t)cfg->mode & VSTVEC_MODE_MASK);
    vstvec_write(tvec_val);
    vs_trap_clear();
}

void vs_trap_setup_direct(uintptr_t handler_addr) {
    vs_trap_config_t cfg = {
        .handler_base = handler_addr,
        .mode = VSTVEC_MODE_DIRECT,
        .num_entries = 0,
    };
    vs_trap_setup(&cfg);
}

/* ===================================================================
 * vs_trap_setup_framework - install the framework's own VS entry
 *
 * This is the STANDING VS endpoint: hyp_reset_state() calls it on every reset,
 * so the VS level always has a handler, exactly as M and S always do.  The
 * delegation baseline depends on it - tsbi_design_brief.md section 4 delegates
 * ordinary guest stimulus down to VS and section 5 calls that the normal main
 * path, which is only meaningful if something is listening there.
 *
 * What it provides is the T-SBI dispatch layer: a VU/VS requester's ECALL_TEST
 * and S-level CSR proxy get served in place, and everything above VS's
 * authority is forwarded up the VS->HS->M chain.
 *
 * A suite may still install its own stub over it with vs_trap_setup_direct(),
 * which is how the suites whose own VS handler is the object under test keep
 * control of that level.  Doing so gives up T-SBI dispatch at VS: a minimal
 * stub has no trap frame to carry the protocol's a0/a1/a2.
 * =================================================================== */
void vs_trap_setup_framework(void) {
    vs_trap_setup_direct((uintptr_t)_vs_trap_entry);
}

/* ===================================================================
 * VS trap record access
 * =================================================================== */

vs_trap_record_t *vs_trap_get_last(void) {
    return &_vs_trap_record;
}

void vs_trap_clear(void) {
    _vs_trap_record.vs_cause = 0;
    _vs_trap_record.vs_epc = 0;
    _vs_trap_record.vs_tval = 0;
    _vs_trap_record.vs_tvec = 0;
    _vs_trap_record.entry_idx = -1;
    _vs_trap_record.triggered = false;
}

bool vs_trap_was_triggered(void) {
    return _vs_trap_record.triggered;
}

/* Scalar views of the last VS trap. trap.c's generic accessors
 * (trap_was_triggered / trap_get_cause / epc / tval) merge these so a
 * hedeleg-delegated stimulus trap is observable through the SAME API as an
 * M/HS one. trap.c cannot include this header (circular via test_framework.h),
 * so it declares these locally as extern. */
uintptr_t vs_trap_get_cause(void) {
    return _vs_trap_record.vs_cause;
}

uintptr_t vs_trap_get_epc(void) {
    return _vs_trap_record.vs_epc;
}

uintptr_t vs_trap_get_tval(void) {
    return _vs_trap_record.vs_tval;
}

/* ===================================================================
 * VS trap record population (called by VS-mode trap handler stub)
 *
 * This function is called from the VS-mode trap handler assembly
 * after saving context. It reads vscause/vsepc/vstval and populates
 * the record. The entry_idx parameter is passed from the vectored
 * stub (or -1 for Direct mode).
 * =================================================================== */

void _vs_trap_record_entry(int entry_idx) {
    /* Read VS CSRs — from VS-mode these are the "native" names:
     * scause=vscause, sepc=vsepc, stval=vstval, stvec=vstvec */
    uintptr_t cause, epc, tval, tvec;
    asm volatile ("csrr %0, scause" : "=r"(cause) :: "memory");
    asm volatile ("csrr %0, sepc"   : "=r"(epc)   :: "memory");
    asm volatile ("csrr %0, stval"  : "=r"(tval)  :: "memory");
    asm volatile ("csrr %0, stvec"  : "=r"(tvec)  :: "memory");

    _vs_trap_record.vs_cause = cause;
    _vs_trap_record.vs_epc = epc;
    _vs_trap_record.vs_tval = tval;
    _vs_trap_record.vs_tvec = tvec;
    _vs_trap_record.entry_idx = entry_idx;
    _vs_trap_record.triggered = true;
}

/* ===================================================================
 * vs_trap_handler - C body of the framework VS entry (hyp_vs_trap_asm.S)
 *
 * Two layers in one function, exactly like the M/S/HS handlers, separated
 * only by the order of the stages (tsbi_design_brief.md section 3):
 *
 *   dispatch layer : P0/P1/P2 below.  P0 and P1 are the shared ones from
 *                    trap.c - privilege-agnostic, because at V=1 the plain S
 *                    CSR names alias the virtual ones.  P2 is the VS flavour,
 *                    which serves the little it may and forwards the rest up
 *                    the VS->HS->M chain.
 *   test-trap layer: everything after them - record the stimulus, step over
 *                    the offending instruction, let the test assert.
 *
 * The order is load-bearing and is the reason this function exists rather than
 * the asm calling _vs_trap_record_entry() directly: a request we served is
 * framework traffic, and letting it reach the record would make
 * vs_trap_was_triggered() fire for a trap no test asked about.
 *
 * @frame: the x1-x31 frame built by SAVE_CONTEXT; the protocol's a0/a1/a2 live
 *         in slots TSBI_FRAME_A0/A1/A2 and the result must be written back
 *         there (RESTORE_CONTEXT reloads a0 from the frame).
 *
 * No return value: VS has exactly one way out, so unlike m_/s_trap_handler
 * there is no xret flavour for the caller to select.
 * =================================================================== */
void vs_trap_handler(uintptr_t *frame) {
    /* scause/sepc = vscause/vsepc at V=1. */
    uintptr_t cause = CSRR(scause);
    uintptr_t epc   = CSRR(sepc);

    /* P0: a fault taken by an instruction our own CSR proxy injected. */
    if (tsbi_s_proxy_capture(cause))
        return;

    /* P1 + P2: raw-ecall escape, then VS-level service dispatch. */
    if (!tsbi_raw_ecall_consume(cause) && tsbi_vs_dispatch(frame, cause, epc))
        return;

    /* ---- Test-trap layer ---- */
    _vs_trap_record_entry(-1);

    /* An interrupt's victim instruction never ran, so it must be re-executed:
     * leave vsepc alone.  Clearing the source is the injector's business (a VS
     * handler has no hvip), so this only records. */
    if (cause & CAUSE_INTERRUPT_BIT)
        return;

    /* CFI (Zicfilp): clear the previous-ELP state before resuming, mirroring
     * what m_trap_handler and hs_trap_handler do for their own level.  A
     * synchronous trap taken into VS-mode saves ELP into vsstatus.SPELP
     * (norm:vsstatus_spelp_op) and the sret below restores ELP from it
     * (norm:Zicfilp_pelp_trap_return), so leaving it set makes the first
     * instruction at the resume PC take a second, spurious software-check --
     * which then overwrites the record of the fault actually under test.
     * At V=1 the `sstatus` name addresses vsstatus, so this clears the guest's
     * own SPELP.  g_trap_preserve_pelp=1 opts out for the cases that verify
     * hardware xRET restores ELP. */
#if __riscv_xlen > 32
    if (!g_trap_preserve_pelp)
        CSRC(sstatus, VSSTATUS_SPELP_BIT);
#endif

    /* Synchronous: step over the offending instruction so the guest makes
     * progress.  Instruction-FETCH faults are the exception - vsepc points at
     * an address that cannot be fetched, so epc+2/4 stays inside the same bad
     * page and re-faults forever.  Those resume at the frame's ra instead, the
     * return address of the call that jumped into the bad target; this is the
     * convention the suites' own VS stubs already use (Sha/tests/sha_strap.S).
     * Reading the instruction at vsepc for its width is only safe once that
     * case is out of the way.
     *
     * ILLEGAL_INST and BREAKPOINT are NOT fetch faults: the instruction was
     * fetched successfully and is merely illegal in context (e.g. WFI with
     * mstatus.TW=1, or an ebreak), so vsepc is readable and stepping over it is
     * correct - exactly what hs_trap_handler's default branch does.  Resuming
     * them at ra jumped to a bogus PC (HSTAT-06 crashed at 0x4 before the
     * fetch-fault set was narrowed to just the three causes below). */
    uintptr_t code = cause & ~CAUSE_INTERRUPT_BIT;
    if (code == CAUSE_INST_ACCESS_FAULT || code == CAUSE_INST_PAGE_FAULT ||
        code == CAUSE_INST_ADDR_MISALIGN) {
        CSRW(sepc, frame[TSBI_FRAME_RA]);
        return;
    }

    uint16_t inst_lo = *(volatile uint16_t *)epc;
    CSRW(sepc, epc + ((inst_lo & 0x3) == 0x3 ? 4 : 2));
}

/* ===================================================================
 * vstvec Vectored mode probe
 * =================================================================== */

bool vstvec_supports_vectored(void) {
    uintptr_t saved = vstvec_read();
    vstvec_write((saved & VSTVEC_BASE_MASK) | VSTVEC_MODE_VECTORED);
    int mode = vstvec_get_mode();
    vstvec_write(saved);
    return (mode == VSTVEC_MODE_VECTORED);
}
