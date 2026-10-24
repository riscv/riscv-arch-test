/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * common/hyp/hyp_reset.c — clean-slate reset of all H-ext state
 * =================================================================== */

#include "hyp_reset.h"
#include "hyp_csr.h"
#include "hyp_vs_trap.h"
#include "encoding.h"

extern void reset_state(void);   /* base reset in test_framework.c */
extern unsigned get_current_priv(void);
extern void goto_priv(unsigned target);

/* ===================================================================
 * PMP bootstrap for V=1 execution
 *
 * QEMU virt with -bios none leaves all PMP entries at reset value
 * (cfg=0, addr=0). With H-extension enabled, V=1 (VS/VU) accesses
 * are checked against PMP just like ordinary S/U accesses, so a
 * zero-CSR PMP denies *every* S/U/V instruction fetch and data
 * access — the very first `mret` into a VS-mode trampoline then
 * immediately raises mcause=1 (instruction access fault).
 *
 * The G-stage tests here run inside a single trusted image, so we
 * install one wide-open PMP entry covering the whole 64-bit address
 * space (RWX for S/U/V). We do this exactly once per reset; further
 * calls are idempotent (the same value is rewritten).
 *
 * Encoding: pmpaddr0 = (1<<54)-1  (all-ones in the low 54 bits, so
 * the NAPOT range is the entire space starting at 0). pmpcfg0[7:0] =
 * R|W|X | A=NAPOT (0x18) = 0x1F. Not locked (L=0) so test code that
 * deliberately pokes PMP later can still take effect.
 * =================================================================== */
static void hyp_pmp_open_all(void) {
    uintptr_t napot_all = ~(uintptr_t)0 >> 10; /* (1<<54)-1 — full NAPOT */
    CSRW(CSR_PMPADDR0, napot_all);
    /* R=1, W=1, X=1, A=NAPOT(3) → byte = 0x1F. Place in entry 0. */
    uintptr_t cfg = 0x1FUL;
    CSRW(CSR_PMPCFG0, cfg);
}

void hyp_reset_state(void) {
    /* Raise to M first, exactly as reset_state() does.  Under the
     * S-mode-normal model the test body runs in S, but this function pokes
     * M-level CSRs directly (pmpaddr0/pmpcfg0 = 0x3A0/0x3B0, menvcfg = 0x30A,
     * mtval2/mtinst = 0x34A/0x34B); from S every one of them raises an
     * illegal-instruction exception.  Going through the T-SBI CSR proxy per
     * write would work too, but a single excursion is both cheaper and what
     * the rest of the framework does - and reset_state() below leaves us in
     * M anyway, so the exit contract is unchanged. */
    if (get_current_priv() != PRIV_M)
        goto_priv(PRIV_M);

    /* ----- PMP: ensure VS/VU accesses are not blanket-denied ----- */
    hyp_pmp_open_all();

    /* ----- HS-level hypervisor CSRs ----- */
    hgatp_set_bare();           /* hgatp = Bare + HFENCE.GVMA all */
    hedeleg_write(0);
    hideleg_write(0);
    /* hie / hip / hvip / hgeie are interrupt-related — clear hvip + hie. */
    CSRW(CSR_HIE, 0);
    CSRW(CSR_HVIP, 0);
    CSRW(CSR_HGEIE, 0);

    /* hstatus: clear VTSR/VTW/VTVM/HU/SPV/SPVP/GVA. Preserve VSXL
     * (it is WARL on RV64; writing 0 may be ignored, but is fine). */
    hstatus_write(0);

    /* ----- M-mode menvcfg: force ADUE=0 -----
     *
     * Per norm:menvcfg_adue_op (machine.adoc), menvcfg.ADUE controls
     * G-stage A/D update behavior:
     *   ADUE=1 -> hardware auto-updates A/D bits (Svadu enabled)
     *   ADUE=0 -> behaves as Svade: page-fault when A/D needs setting
     *             (norm:Svadu_disabled_hw_update_falls_back_to_svade,
     *              svade in supervisor.adoc)
     *
     * QEMU 8.2.94 default `-cpu rv64,h=true` resets menvcfg.ADUE=1,
     * which silently breaks tests that expect Svade fault semantics
     * (sv39x4 GAD-01/02/03). Force ADUE=0 here to put every test
     * onto the spec-mandated Svade path. See diagnostic report at
     * docs/gad_diagnose_report.md for full root-cause analysis.
     *
     * Preserve PBMTE and other bits (Svpbmt etc.) -- only clear ADUE.
     * Per norm:menvcfg_adue_henvcfg_adue_rdonly0, this also forces
     * henvcfg.ADUE to read-only zero, so the henvcfg_write(0) below
     * remains effective.
     *
     * SFENCE.VMA synchronizes address-translation caches w.r.t. the
     * new A/D interpretation (norm:menvcfg_adue_fence); the trailing
     * hfence_gvma_all() at the end of this function further covers
     * G-stage caches (hyp-mm-fences).
     *
     * Also clear the Zicfilp/Zicfiss enables (LPE/SSE) here: an henvcfg
     * test sets menvcfg.LPE to make henvcfg.LPE writable and only clears
     * henvcfg afterwards, so without this the suite would leak S-mode
     * landing-pad enforcement to whatever runs next (no hart reset),
     * causing software-check exceptions (mcause=18) in unrelated suites.
     * Gated on the platform's Zicfilp/Zicfiss declaration, matching
     * reset_state() in common/test_framework.c.
     * Preserve PBMTE and other unrelated bits. */
    {
        uintptr_t clr = MENVCFG_ADUE;
#if ZICFILP_AVAILABLE
        clr |= MENVCFG_LPE;
#endif
#if ZICFISS_AVAILABLE
        clr |= MENVCFG_SSE;
#endif
        uintptr_t mv = csr_read(CSR_MENVCFG);
        csr_write(CSR_MENVCFG, mv & ~clr);
        asm volatile ("sfence.vma" ::: "memory");
    }

    henvcfg_write(0);
    hcounteren_write(0);
    htimedelta_write(0);

    /* htval / htinst are read-only side-effects of traps; clearing
     * them is not strictly required, but keeps the trap_record clean. */
    CSRW(CSR_HTVAL, 0);
    CSRW(CSR_HTINST, 0);

    /* mtval2 / mtinst (M-mode counterparts): clear so a stale value
     * from a previous test cannot be mistaken for a hardware-written
     * trap value (MTVAL/TINST strict checks). Both are WARL and must
     * hold zero (norm:mtval2_val / norm:mtinst_val). */
    CSRW(CSR_MTVAL2, 0);
    CSRW(CSR_MTINST, 0);

    /* ----- VS-level CSRs ----- */
    CSRW(CSR_VSSTATUS, 0);
    CSRW(CSR_VSIE, 0);
    CSRW(CSR_VSSCRATCH, 0);
    CSRW(CSR_VSEPC, 0);
    CSRW(CSR_VSCAUSE, 0);
    CSRW(CSR_VSTVAL, 0);
    CSRW(CSR_VSIP, 0);
    CSRW(CSR_VSATP, 0);

    /* vstvec is NOT cleared: the VS level gets its standing handler instead.
     * The delegation baseline sends ordinary guest stimulus down to VS (see
     * tsbi_deleg_hedeleg_baseline / brief section 4), so a cleared vstvec would
     * route those traps to address 0 rather than to a handler.  M and S have a
     * permanent entry installed at boot; this gives VS the same.  A suite whose
     * own VS handler is the object under test overrides it per case with
     * vs_trap_setup_direct(), and this reset puts the framework entry back. */
    vs_trap_setup_framework();

    /* Final TLB flush: vsatp was just cleared, so flush the VS-stage
     * (HFENCE.VVMA) as well as any lingering G-stage entries
     * (HFENCE.GVMA).  Flushing only GVMA would leave stale VS-stage
     * entries from a prior paged vsatp usable by the next VS run. */
    hfence_vvma_all();

    /* Final TLB flush in case any G-stage entries linger. */
    hfence_gvma_all();

    /* ----- Forward to base reset (PMP, satp, M-mode return, etc.) ----- */
    reset_state();
}

bool hyp_misa_h(void)
{
    /* misa is M-level; from S the csrr below would trap.  Same excursion the
     * reset above takes, and just as cheap when we are already in M. */
    if (get_current_priv() != PRIV_M)
        goto_priv(PRIV_M);

    uintptr_t misa;
    asm volatile ("csrr %0, misa" : "=r"(misa));
    return (misa & (1UL << ('H' - 'A'))) != 0;
}

void hyp_reset_state_if_h(void)
{
    if (hyp_misa_h())
        hyp_reset_state();      /* forwards to reset_state() itself */
    else
        reset_state();
}
