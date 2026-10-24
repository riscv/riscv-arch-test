/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * common/hyp/hyp_priv.c — VS / VU mode execution helpers
 *
 * Implementation strategy:
 *   - Reuse the existing run_in_priv() trampoline pattern from
 *     common/privilege.c, but enter the trampoline with V=1 by
 *     setting mstatus.MPV (RV64 bit 39) before mret.
 *   - The trampoline ends with `ecall`, which (in VS-mode) reports
 *     CAUSE_ECALL_FROM_VS=10. The M-mode ecall handler in trap.c
 *     accepts cause 10 as a privilege-switch ecall and returns to
 *     M-mode normally (clearing MPV).
 *
 * NOTE: We must enter VS-mode from M-mode directly (not via S-mode),
 *       because mstatus.MPV is only consulted by mret. Therefore
 *       these helpers internally hop to M-mode first if necessary.
 * =================================================================== */

#include "hyp_priv.h"
#include "encoding.h"
#include "uart.h"
#include "tsbi/tsbi.h"
#include "hyp/hyp_csr.h"

extern unsigned current_priv;

/* ===================================================================
 * Trampoline state
 * =================================================================== */
static uintptr_t (*_v_run_fn)(uintptr_t);
static uintptr_t   _v_run_arg;
static uintptr_t   _v_run_result;

/* The trampoline runs in VS- or VU-mode. It calls fn(arg) and then
 * issues `ecall` to return to M-mode. The trap handler sets mepc to
 * the instruction *after* the ecall (the `ret`), and configures
 * MPP back to M-mode and clears MPV, so mret returns here in M-mode.
 * Then `ret` jumps to ra, which we set to a label in the caller. */
static void __attribute__((used)) _v_trampoline(void) {
    /* Invoke the test function via an indirect call with rs1=x7 (t2).
     * Per Zicfilp (norm:zicflip_lpad_expected), a JALR with rs1=x1/x5/x7
     * does not set ELP to LP_EXPECTED, so this framework-internal call
     * stays transparent to landing-pad enforcement when a test enables
     * xLPE in VS/VU-mode. The test's own indirect jumps still exercise
     * the LP_EXPECTED path. A compiler-generated call could use any
     * scratch register (e.g. a5=x15) and would spuriously fault.
     *
     * rs1=x7 (not x5) is chosen deliberately: with Zicfiss enabled, a
     * JALR with rd=x1 and rs1=x5 is a coroutine swap (sspopchk x5 +
     * sspush x1) which would fault on the shadow stack, whereas
     * rd=x1 with rs1 outside {x1,x5} remains a plain call (sspush x1),
     * matching the original compiler-generated behavior. */
    asm volatile (
        "ld   a0, %[arg]\n\t"
        "ld   t2, %[fn]\n\t"
        "jalr ra, t2, 0\n\t"
        "sd   a0, %[res]\n\t"
        :
        : [fn] "m"(_v_run_fn), [arg] "m"(_v_run_arg),
          [res] "m"(_v_run_result)
        : "a0", "a1", "a2", "a3", "a4", "a5", "a6", "a7",
          "t0", "t1", "t2", "t3", "t4", "t5", "t6", "ra", "memory"
    );
    /* Ask to be put back in M-mode.  This MUST use the T-SBI wire protocol
     * (opcode in a0): the legacy ecall_args[] tag is dead - trap.c keeps the
     * array only so old writers still compile, and ignores its contents.  A
     * bare ecall here would therefore hand the handler whatever a0 the test
     * payload happened to leave behind as an "opcode", the request would be
     * dropped, and we would sret straight back into VS/VU - leaving the test
     * body running at V=1 and faulting on its next HS-level CSR access.
     *
     * The result is already parked in _v_run_result above, so tsbi_ecall()
     * overwriting a0/a1 costs us nothing. */
    (void)tsbi_ecall(tsbi_priv_to_goto(PRIV_M), 0);
}

/* ===================================================================
 * Common implementation
 *
 * @target: PRIV_VS (5) or PRIV_VU (4) — bit 2 marks V=1, low 2 bits
 *          give nominal MPP (S=1 / U=0).
 * =================================================================== */
static uintptr_t run_in_virt_priv(unsigned target,
                                  uintptr_t (*fn)(uintptr_t),
                                  uintptr_t arg)
{
    /* Make sure we are in M-mode so that mret with MPV=1 takes effect. */
    extern void goto_priv(unsigned);
    if (current_priv != PRIV_M)
        goto_priv(PRIV_M);

    _v_run_fn     = fn;
    _v_run_arg    = arg;
    _v_run_result = 0;

    /* Configure mstatus:
     *   - clear MPP, set MPP to (target & 3)
     *   - set MPV (bit 39) so mret enters V=1
     *   - clear MPRV (bit 17)
     *   - set MPIE so interrupts behave normally after mret
     */
    uintptr_t ms = CSRR(mstatus);
    ms &= ~((3UL << 11) | (1UL << 17) | MSTATUS_MPV);
    ms |=  ((uintptr_t)(target & 3) << 11);
    ms |=  MSTATUS_MPV;
    CSRW(mstatus, ms);

    /* Update tracked privilege so subsequent ecall returns set MPV/MPP correctly. */
    current_priv = target;

    /* Ensure the trampoline's return ecall always traps straight to
     * M-mode. The ecall is executed in the target mode, so its cause
     * depends on that mode: ecall-from-VS is CAUSE_ECALL_FROM_VS (10),
     * while ecall-from-VU reports CAUSE_ECALL_FROM_U (8) -- under V=1
     * the "from U" code carries the VU ecall. The T-SBI delegation
     * baseline delegates BOTH causes down toward the VS/HS handlers
     * (the normal guest-request path), but this ecall is a framework-
     * internal "return to M" request: the multi-level VS->HS->M
     * forwarding chain rebuilds a guest's resume point, not this
     * M-mode caller's, so it cannot serve the trampoline. Un-delegate
     * the cause the target mode will actually raise so the ecall
     * lands in M directly -- the VS path already relied on this, the
     * VU path was simply clearing the wrong bit. */
    uintptr_t ecall_cause = (target == PRIV_VU) ? CAUSE_ECALL_FROM_U
                                                : CAUSE_ECALL_FROM_VS;

    uintptr_t md = CSRR(medeleg);
    md &= ~(1UL << ecall_cause);
    CSRW(medeleg, md);

    uintptr_t hd = hedeleg_read();
    hd &= ~(1UL << ecall_cause);
    hedeleg_write(hd);

    /* Enter VS/VU at _v_trampoline, return here via the ecall round-trip.
     *
     * The ecall handler is a C function that clobbers all caller-saved
     * registers (a0-a7, t0-t6).  The clobber list MUST include them all;
     * otherwise the compiler may assume a register (e.g. a0) still holds
     * a pre-mret value and generate a dereference like `ld a0, 0(a0)`
     * after the round-trip, faulting on the handler's return value. */
    asm volatile (
        "la ra, 1f\n\t"
        "la t0, _v_trampoline\n\t"
        "csrw mepc, t0\n\t"
        "mret\n\t"
        "1:\n\t"
        ::: "ra", "t0", "t1", "t2", "t3", "t4", "t5", "t6",
            "a0", "a1", "a2", "a3", "a4", "a5", "a6", "a7", "memory"
    );

    /* On return current_priv has been reset to PRIV_M by the ecall handler. */
    return _v_run_result;
}

uintptr_t run_in_vs_mode(uintptr_t (*fn)(uintptr_t), uintptr_t arg) {
    return run_in_virt_priv(PRIV_VS, fn, arg);
}

uintptr_t run_in_vu_mode(uintptr_t (*fn)(uintptr_t), uintptr_t arg) {
    return run_in_virt_priv(PRIV_VU, fn, arg);
}

/* ===================================================================
 * Direct privilege-level switching
 *
 * These are lower-level than run_in_vs/vu_mode — they switch
 * privilege but do NOT set up a return trampoline. The caller must
 * arrange the return path (e.g., ecall → return_to_hs_mode).
 *
 * NOTE: goto_vs_mode works via M-mode mret (setting MPV=1) since
 * the test framework always traps to M-mode. It sets mepc to the
 * return address of the caller so execution continues there in
 * VS-mode.
 * =================================================================== */

void __attribute__((noreturn)) goto_vs_mode(void) {
    /* Ensure we are in M-mode first */
    extern void goto_priv(unsigned);
    if (current_priv != PRIV_M)
        goto_priv(PRIV_M);

    /* Set mstatus: MPP=S(1), MPV=1, clear MPRV */
    uintptr_t ms = CSRR(mstatus);
    ms &= ~((3UL << 11) | (1UL << 17) | MSTATUS_MPV);
    ms |= (1UL << 11);     /* MPP = S */
    ms |= MSTATUS_MPV;     /* V=1 on mret */
    CSRW(mstatus, ms);

    current_priv = PRIV_VS;

    /* mret to the instruction after this function returns.
     * We set mepc = ra (return address of caller). */
    asm volatile (
        "csrw mepc, ra\n\t"
        "mret\n\t"
        ::: "memory"
    );
    __builtin_unreachable();
}

void __attribute__((noreturn)) goto_vu_mode(void) {
    /* Ensure we are in M-mode first */
    extern void goto_priv(unsigned);
    if (current_priv != PRIV_M)
        goto_priv(PRIV_M);

    /* Set mstatus: MPP=U(0), MPV=1, clear MPRV */
    uintptr_t ms = CSRR(mstatus);
    ms &= ~((3UL << 11) | (1UL << 17) | MSTATUS_MPV);
    /* MPP = U (bits [12:11] = 0) — already cleared */
    ms |= MSTATUS_MPV;     /* V=1 on mret */
    CSRW(mstatus, ms);

    current_priv = PRIV_VU;

    asm volatile (
        "csrw mepc, ra\n\t"
        "mret\n\t"
        ::: "memory"
    );
    __builtin_unreachable();
}

void return_to_hs_mode(void) {
    /* Same T-SBI request the trampoline issues; see _v_trampoline for why a
     * bare ecall is not interchangeable with this. */
    (void)tsbi_ecall(tsbi_priv_to_goto(PRIV_M), 0);
}

unsigned get_virt_priv(void) {
    return current_priv;
}
