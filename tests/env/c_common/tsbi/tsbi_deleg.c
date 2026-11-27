/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 *
 * tsbi_deleg.c - T-SBI delegation baseline (delegation-first model)
 *
 * DESIGN (tsbi_design_brief.md section 4):
 *   Nothing makes a per-request routing decision in software.  Where a trap
 *   lands is decided by hardware at trap time from "originating privilege +
 *   delegation bits", and those bits are written once at boot.  The rule is
 *   "services go up, accidents stay local":
 *
 *     - stimulus traps from S/U      -> delegated, land in the S handler
 *     - ecall-from-S (cause 9)       -> NEVER delegated, lands in M
 *                                       (the T-SBI service channel)
 *     - VS/VU traps                 -> two-level: medeleg then hedeleg
 *
 *   Baseline values are NOT hard-coded constants: they are assembled from the
 *   platform capability macros in rvtest_config.h, written, then read back so
 *   the effective value (after WARL / read-only-zero bits) is what we keep as
 *   the restore target.
 *
 * INVARIANT: medeleg[9] (ecall-from-S) must stay 0.  Delegating it would send
 * run_in_priv()'s return ecall to the S handler, whose GOTO branch issues
 * another ecall to M, looping forever.  tsbi_delegate_exc() refuses that bit.
 */

#include "types.h"
#include "encoding.h"
#include "cause_defs.h"
#include "tsbi.h"

/* Runtime CSR access by address (csr_accessors.c) - used for the optional
 * H-extension registers so this file compiles on platforms without them. */
extern uintptr_t csr_read(uint16_t csr);
extern void      csr_write(uint16_t csr, uintptr_t val);

/* Privilege control (privilege.c): the M-safe bulk setters at the bottom of
 * this file raise to M for the medeleg/mideleg write and drop back, so they
 * work under the S-mode-normal model where the caller is usually in S(HS). */
extern unsigned get_current_priv(void);
extern void     goto_priv(unsigned target);

#ifndef CSR_HEDELEG
#define CSR_HEDELEG   0x602
#endif
#ifndef CSR_HIDELEG
#define CSR_HIDELEG   0x603
#endif

#define TSBI_BIT(n)   ((uintptr_t)1u << (n))

/* hedeleg/hideleg are HS-level CSRs, so the second delegation level exists
 * only for a build that owns hypervisor state.  H_SUPPORTED alone is not
 * enough: it comes from the platform config (rvtest_config.h), which every
 * suite of that platform shares, so a single-stage Sv or Ss suite built
 * without ENABLE_HYP still sees it set.  csr_accessors.c compiles the H CSR
 * dispatch entries out under ENABLE_HYP, so a by-number csr_write(CSR_HEDELEG)
 * from such a suite lands on the "absent from the dispatch table" error path
 * and silently no-ops.  Gate both levels on the same pair of conditions. */
#if defined(H_SUPPORTED) && defined(ENABLE_HYP)
#define TSBI_DELEG_HAS_H 1
#else
#define TSBI_DELEG_HAS_H 0
#endif

/* ===================================================================
 * Effective baseline snapshot
 *
 * Filled by tsbi_deleg_apply_baseline() from the values actually read back
 * after the write.  Bits the hardware refuses (read-only-zero) therefore
 * never appear here, which also tells us where a software Delegate Relay
 * fallback would be required on that platform.
 * =================================================================== */
static uintptr_t tsbi_medeleg_effective;
static uintptr_t tsbi_mideleg_effective;
#if TSBI_DELEG_HAS_H
static uintptr_t tsbi_hedeleg_effective;
static uintptr_t tsbi_hideleg_effective;
#endif
static bool      tsbi_deleg_initialised;

/* ===================================================================
 * tsbi_deleg_medeleg_baseline - which exceptions go to the S handler
 *
 * Mirrors the adoc S-mode boot value 0xFCB5FF bit by bit
 * (tsbi_design_brief.md section 4 table):
 *
 *   bit 0..7   misaligned / access fault / illegal inst(2) / breakpoint(3)
 *              -> 1, ordinary stimulus, consumed in place by the S handler
 *   bit 8      ecall-from-U            -> 1, U's T-SBI request reaches S first
 *   bit 9      ecall-from-S            -> 0, T-SBI SERVICE CHANNEL (invariant)
 *   bit 10     ecall-from-VS           -> 1, hedeleg then decides HS vs VS
 *   bit 11     ecall-from-M            -> 0, architecturally read-only-zero
 *   bit 12/13/15 inst/load/store page fault -> 1, ordinary stimulus
 *   bit 14/17  reserved                -> 0
 *   bit 16     double trap             -> 0, must be handled by M
 *   bit 18/19  software check / hardware error -> 1 when the extension exists
 *   bit 20..23 guest page faults / virtual instruction -> 1 (H only); hedeleg
 *              keeps them in HS since those bits are read-only-zero there
 * =================================================================== */
uintptr_t tsbi_deleg_medeleg_baseline(void)
{
    uintptr_t v = 0;

    /* bits 0..7: base synchronous exceptions */
    v |= TSBI_BIT(CAUSE_INST_ADDR_MISALIGN);
    v |= TSBI_BIT(CAUSE_INST_ACCESS_FAULT);
    v |= TSBI_BIT(CAUSE_ILLEGAL_INST);
    v |= TSBI_BIT(CAUSE_BREAKPOINT);
    v |= TSBI_BIT(CAUSE_LOAD_ADDR_MISALIGN);
    v |= TSBI_BIT(CAUSE_LOAD_ACCESS_FAULT);
    v |= TSBI_BIT(CAUSE_STORE_ADDR_MISALIGN);
    v |= TSBI_BIT(CAUSE_STORE_ACCESS_FAULT);

    /* bit 8 (ecall-from-U): DELEGATED, matching the adoc boot value 0xFCB5FF
     * and tsbi_design_brief.md section 4.
     *
     * Delegating it needed TWO things, and both are now in place.
     *
     * The first is the handover on a forwarded GOTO_MMODE.  M lands its mret on
     * the ORIGINAL requester, so the register context M restores must be the
     * requester's, not the forwarding handler's.  A C function cannot arrange
     * that - the compiler owns sp/s0/ra inside s_trap_handler - and the mret
     * used to return with the S handler's context, spinning FW-DOWN-02 (U->M)
     * forever.  _tsbi_forward_goto now lives in trap_asm.S and restores the
     * requester's full register set from the frame before the bare ecall;
     * TSBI-DELEG-06 asserts that handover directly.
     *
     * The second exists only under H, where this same bit number also carries
     * ecall-from-VU, and is a question of WHERE a VU request lands.  A V=1 trap
     * needs medeleg[C]=1 AND hedeleg[C]=1 to reach the VS handler.  The brief
     * (section 4 table, and chain 1 of section 5) delegates both, so a VU
     * request is served by the VS handler and forwarded up the VS->HS->M chain
     * if that level cannot serve it.  That is what hedeleg does below, and it
     * is why the VS entry is installed as a standing endpoint at reset - see
     * the hedeleg baseline for the full reasoning.
     *
     * Only ecall is affected.  Other U-mode stimulus (illegal inst, page
     * faults, ...) is delegated to the S handler above regardless, so the
     * S-mode-normal model is unchanged. */
    v |= TSBI_BIT(CAUSE_ECALL_FROM_U);

    /* bit 9 (ecall-from-S) stays omitted - the one service channel that must
     * never be delegated.  Delegating it would make the S handler's own
     * forwarding ecall land back in S, overwriting the sepc that holds the
     * requester's return address (framework invariant; trap_delegate_exc()
     * refuses this bit).  bit 11 (ecall-from-M) is read-only-zero anyway. */

    /* bits 12/13/15: page faults (main stimulus for the VM suites) */
    v |= TSBI_BIT(CAUSE_INST_PAGE_FAULT);
    v |= TSBI_BIT(CAUSE_LOAD_PAGE_FAULT);
    v |= TSBI_BIT(CAUSE_STORE_PAGE_FAULT);

    /* bit 16 (double trap) intentionally omitted - must stay in M. */

#ifdef H_SUPPORTED
    /* bit 10: VS's T-SBI requests; hedeleg[10] is read-only-zero so these
     * still stop at HS, but medeleg must delegate them out of M first. */
    v |= TSBI_BIT(CAUSE_ECALL_FROM_VS);
    /* bits 20..23: guest page faults and virtual instruction - HS-level
     * events; delegating them out of M lets the HS handler see them. */
    v |= TSBI_BIT(CAUSE_INST_GUEST_PAGE_FAULT);
    v |= TSBI_BIT(CAUSE_LOAD_GUEST_PAGE_FAULT);
    v |= TSBI_BIT(CAUSE_VIRTUAL_INSTRUCTION);
    v |= TSBI_BIT(CAUSE_STORE_GUEST_PAGE_FAULT);
#endif

#ifdef ZICFILP_SUPPORTED
    /* bit 18: software check (CFI landing-pad / shadow-stack violations) */
    v |= TSBI_BIT(CAUSE_SOFTWARE_CHECK);
#endif

    return v;
}

/* ===================================================================
 * tsbi_deleg_mideleg_baseline - which interrupts go to the S handler
 *
 * Mirrors the adoc value 0x366: supervisor software/timer/external plus, on
 * H platforms, the VS-level bits (which are read-only-one there anyway).
 * LCOFI joins when the counter-overflow extension exists.  M-level
 * interrupts (MSI/MTI/MEI) are architecturally non-delegatable.
 * =================================================================== */
uintptr_t tsbi_deleg_mideleg_baseline(void)
{
    uintptr_t v = 0;

    v |= TSBI_BIT(1);   /* SSI  - supervisor software */
    v |= TSBI_BIT(5);   /* STI  - supervisor timer    */
    v |= TSBI_BIT(9);   /* SEI  - supervisor external */

#ifdef H_SUPPORTED
    v |= TSBI_BIT(2);   /* VSSI */
    v |= TSBI_BIT(6);   /* VSTI */
    v |= TSBI_BIT(10);  /* VSEI */
#endif

#ifdef SSCOFPMF_SUPPORTED
    v |= TSBI_BIT(13);  /* LCOFI - counter overflow */
#endif

    return v;
}

#ifdef H_SUPPORTED
/* ===================================================================
 * tsbi_deleg_hedeleg_baseline - second-level: HS vs VS
 *
 * A VS/VU trap needs medeleg[C]=1 AND hedeleg[C]=1 to reach the VS handler;
 * with hedeleg[C]=0 it stops at HS.  Per tsbi_design_brief.md section 4
 * ("hedeleg 基线") the baseline delegates the ordinary stimulus a guest can
 * raise, so that it is handled closest to where it happened -- section 5
 * calls VU stimulus delivered straight to the VS handler the 常态主路径
 * (normal main path), exactly mirroring what medeleg does one level up.
 *
 * This requires a STANDING VS endpoint, which is what the framework VS entry
 * in hyp_vs_trap_asm.S provides: hyp_reset_state() installs it into vstvec on
 * every reset, so the VS level always has a handler, just as M and S do.  A
 * suite that installs its own stub over it takes that level over deliberately.
 *
 *   bits 0..7   misaligned / access fault / illegal inst / breakpoint
 *   bit 8       ecall-from-VU  - the VS handler serves its guest's T-SBI
 *                                requests and forwards what it cannot serve
 *                                up the VS->HS->M chain (brief section 5,
 *                                chain 1)
 *   bits 12/13/15 VS's own first-stage page faults
 *
 * Read-only-zero here, so HS regardless of what is written:
 *   bit 10      ecall-from-VS  - VS's own T-SBI request cannot be handed back
 *                                to itself; this is the VS->HS chain start
 *   bits 20..23 guest page faults / virtual instruction - HS-level events
 *                                (two-stage translation is HS's business)
 * =================================================================== */
uintptr_t tsbi_deleg_hedeleg_baseline(void)
{
    uintptr_t v = 0;

    /* Ordinary stimulus a VU/VS guest can raise -> handle inside the guest */
    v |= TSBI_BIT(CAUSE_INST_ADDR_MISALIGN);
    v |= TSBI_BIT(CAUSE_INST_ACCESS_FAULT);
    v |= TSBI_BIT(CAUSE_ILLEGAL_INST);
    v |= TSBI_BIT(CAUSE_BREAKPOINT);
    v |= TSBI_BIT(CAUSE_LOAD_ADDR_MISALIGN);
    v |= TSBI_BIT(CAUSE_LOAD_ACCESS_FAULT);
    v |= TSBI_BIT(CAUSE_STORE_ADDR_MISALIGN);
    v |= TSBI_BIT(CAUSE_STORE_ACCESS_FAULT);

    /* bit 8: ecall-from-VU -> the VS handler serves its guest's requests */
    v |= TSBI_BIT(CAUSE_ECALL_FROM_U);

    /* VS's own page faults (first-stage) */
    v |= TSBI_BIT(CAUSE_INST_PAGE_FAULT);
    v |= TSBI_BIT(CAUSE_LOAD_PAGE_FAULT);
    v |= TSBI_BIT(CAUSE_STORE_PAGE_FAULT);

    /* bit 10 and bits 20..23 deliberately omitted (read-only-zero) */
    return v;
}

/* ===================================================================
 * tsbi_deleg_hideleg_baseline - second-level interrupt delegation
 *
 * Only the VS-level interrupts can be pushed down to VS, and a bit may be
 * set here only if the corresponding mideleg bit is set (hardware enforces
 * this two-level progression).
 * =================================================================== */
uintptr_t tsbi_deleg_hideleg_baseline(void)
{
    return TSBI_BIT(2) | TSBI_BIT(6) | TSBI_BIT(10);  /* VSSI/VSTI/VSEI */
}
#endif /* H_SUPPORTED */

/* ===================================================================
 * tsbi_deleg_apply_baseline - write the baseline, then snapshot it back
 *
 * Called from boot (before dropping to S) and by reset_state() through
 * tsbi_deleg_restore_baseline().  Must run in M-mode.
 *
 * The read-back matters twice over: it records what the hardware actually
 * accepted (WARL / read-only-zero), and the difference against the intended
 * value is exactly the set of causes that would need the software Delegate
 * Relay fallback on this platform.
 * =================================================================== */
void tsbi_deleg_apply_baseline(void)
{
    /* Under -DTSBI_BOOT_MODE_M (the Sm* machine-level suites) keep the
     * historical M-mode model: the pre-T-SBI entry never programmed
     * medeleg/mideleg, so every trap lands in M unless a test explicitly
     * delegates it.  Zero the baseline and snapshot 0, so reset_state()'s
     * restore cleans up to the same M-landing default between tests instead
     * of re-delegating ordinary exceptions/interrupts down to S. */
#ifdef TSBI_BOOT_MODE_M
    uintptr_t want_med = 0;
    uintptr_t want_mid = 0;
#else
    uintptr_t want_med = tsbi_deleg_medeleg_baseline();
    uintptr_t want_mid = tsbi_deleg_mideleg_baseline();
#endif

    CSRW(medeleg, want_med);
    CSRW(mideleg, want_mid);

    tsbi_medeleg_effective = CSRR(medeleg);
    tsbi_mideleg_effective = CSRR(mideleg);

#if TSBI_DELEG_HAS_H
#ifdef TSBI_BOOT_MODE_M
    csr_write(CSR_HEDELEG, 0);
    csr_write(CSR_HIDELEG, 0);
#else
    /* hideleg requires the matching mideleg bits, which were just written. */
    csr_write(CSR_HEDELEG, tsbi_deleg_hedeleg_baseline());
    csr_write(CSR_HIDELEG, tsbi_deleg_hideleg_baseline());
#endif
    tsbi_hedeleg_effective = csr_read(CSR_HEDELEG);
    tsbi_hideleg_effective = csr_read(CSR_HIDELEG);
#endif

    tsbi_deleg_initialised = true;
}

/* ===================================================================
 * tsbi_deleg_restore_baseline - re-apply the snapshot (reset_state)
 *
 * Must run in M-mode; reset_state() batches this into a single M-mode
 * excursion together with the other M-CSR resets.
 * =================================================================== */
void tsbi_deleg_restore_baseline(void)
{
    if (!tsbi_deleg_initialised) {
        tsbi_deleg_apply_baseline();
        return;
    }

    CSRW(medeleg, tsbi_medeleg_effective);
    CSRW(mideleg, tsbi_mideleg_effective);
#if TSBI_DELEG_HAS_H
    csr_write(CSR_HEDELEG, tsbi_hedeleg_effective);
    csr_write(CSR_HIDELEG, tsbi_hideleg_effective);
#endif
}

uintptr_t tsbi_deleg_effective_medeleg(void) { return tsbi_medeleg_effective; }
uintptr_t tsbi_deleg_effective_mideleg(void) { return tsbi_mideleg_effective; }

/* ===================================================================
 * Per-test delegation switches (with guard rails)
 *
 * Used by suites that need the "undelegated leg" - e.g. a Sm_* case that
 * asserts a trap must land in M has to switch that cause out of the
 * delegation-first baseline first, then let reset_state() restore it.
 *
 * Both run in M-mode: call them inside an M-mode excursion, or from a
 * test already running in M.
 * =================================================================== */
bool tsbi_delegate_exc(unsigned cause)
{
    /* Framework invariant: ecall-from-S must never be delegated. */
    if (cause == CAUSE_ECALL_FROM_S)
        return false;
    /* Architecturally impossible; refuse instead of silently no-op'ing. */
    if (cause == CAUSE_ECALL_FROM_M || cause == CAUSE_DOUBLE_TRAP)
        return false;
    if (cause >= (unsigned)(8 * sizeof(uintptr_t)))
        return false;

    CSRS(medeleg, TSBI_BIT(cause));
    return (CSRR(medeleg) & TSBI_BIT(cause)) != 0;
}

bool tsbi_undelegate_exc(unsigned cause)
{
    if (cause >= (unsigned)(8 * sizeof(uintptr_t)))
        return false;

    CSRC(medeleg, TSBI_BIT(cause));
    return (CSRR(medeleg) & TSBI_BIT(cause)) == 0;
}

/* ===================================================================
 * M-safe bulk delegation setters (single source of truth)
 *
 * medeleg/mideleg are M-level CSRs.  Under the S-mode-normal model the
 * H-extension delegation helpers are invoked from S(HS)-mode, where a direct
 * csrw medeleg traps illegal.  These two primitives own the "raise to M,
 * write, drop back" excursion in ONE place so every caller shares it instead
 * of poking medeleg/mideleg on its own:
 *   - hyp_csr.c         : hyp_delegate_to_vs
 *   - hyp_test_helpers.c: setup_deleg_to_vs / setup_deleg_to_hs /
 *                         clear_all_deleg
 *
 * tsbi_deleg_or() enforces the medeleg[9] (ecall-from-S) invariant by masking
 * that bit out of the OR set, exactly as tsbi_delegate_exc() refuses it -
 * delegating ecall-from-S would dead-loop the T-SBI service channel.
 * Clearing needs no guard (keeping bit 9 at 0 already satisfies it).
 * hedeleg/hideleg are HS-level and stay direct in the callers.
 * =================================================================== */
void tsbi_deleg_or(uintptr_t exc_mask, uintptr_t int_mask)
{
    exc_mask &= ~TSBI_BIT(CAUSE_ECALL_FROM_S);   /* T-SBI service channel */

    unsigned saved = get_current_priv();
    if (saved != PRIV_M)
        goto_priv(PRIV_M);

    if (exc_mask)
        CSRS(medeleg, exc_mask);
    if (int_mask)
        CSRS(mideleg, int_mask);

    if (saved != PRIV_M)
        goto_priv(saved);
}

void tsbi_deleg_clear(uintptr_t exc_mask, uintptr_t int_mask)
{
    unsigned saved = get_current_priv();
    if (saved != PRIV_M)
        goto_priv(PRIV_M);

    if (exc_mask)
        CSRC(medeleg, exc_mask);
    if (int_mask)
        CSRC(mideleg, int_mask);

    if (saved != PRIV_M)
        goto_priv(saved);
}
