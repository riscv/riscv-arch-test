/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * Test Group 6: vsip/vsie alias verification
 *
 * Tests VSIE-01 through VSIE-22 verify vsip/vsie register behavior
 * including V=1 substitution, hideleg-controlled alias chains,
 * interrupt number translation (10->9, 6->5, 2->1), read-only zero
 * WARL behavior, write-direction no-effect when not delegated, direct
 * CSR read/write, alias chain from M-mode, and LCOFI extension.
 *
 * Spec references:
 *   norm:vsip_vsie_sz_acc_op   V=1 substitution
 *   norm:vsip_vsie_sei         VSEIP/VSEIE alias rules
 *   norm:vsip_vsie_sti         VSTIP/VSTIE alias rules
 *   norm:vsip_vsie_ssi         VSSIP/VSSIE alias rules
 *   norm:vsip_vsie_lcofi       LCOFIP/LCOFIE alias rules (Shlcofideleg)
 */

#include "hyp_test_helpers.h"

/* S-level interrupt bit positions in sip/sie (after translation). */
#define SIP_SSIP        (1UL << 1)
/* SIP_STIP already defined in encoding.h */
#define SIP_SEIP        (1UL << 9)

/* VS-level interrupt bit positions in hideleg/hip/hie. */
#define HIDELEG_VSSI    (1UL << 2)
#define HIDELEG_VSTI    (1UL << 6)
#define HIDELEG_VSEI    (1UL << 10)

#define HIE_VSSIE       (1UL << 2)
#define HIE_VSTIE       (1UL << 6)
#define HIE_VSEIE       (1UL << 10)

/* ------------------------------------------------------------------
 * VSIE-01: Verifies that in V=1 mode, reading sip/sie actually accesses
 * vsip/vsie through the CSR substitution mechanism.
 * ------------------------------------------------------------------ */
TEST_REGISTER(test_vsie_01);
bool test_vsie_01(void) {
    TEST_BEGIN("VSIE-01: V=1 sip/sie access vsip/vsie");

    /* --- Part A: sip reads vsip (pending verification) --- */
    /* Delegate VSSI so vsip.SSIP aliases hip.VSSIP. */
    hideleg_write(HIDELEG_VSSI);
    hvip_set_vssi(true);

    /* VS-mode reads sip -> substituted to vsip in V=1.
     *
     * Known QEMU limitation: QEMU does not correctly implement the
     * V=1 sip/sie read-direction alias. M-mode reading vsip(0x244)
     * returns the correct pending value, but VS-mode reading sip
     * always returns 0. The write direction works correctly. */
    uintptr_t sip_val = run_in_vs_mode(vs_read_sip, 0);
    TEST_ASSERT("sip.SSIP reflects VSSIP pending via vsip substitution",
                (sip_val & SIP_SSIP) != 0);
    hvip_set_vssi(false);

    /* --- Part B: sie reads vsie (enable verification) --- */
    /* Set hie.VSSIE -> aliased to vsie.SSIE when delegated. */
    CSRW(CSR_HIE, 0);
    CSRS(CSR_HIE, HIE_VSSIE);

    /* VS-mode reads sie -> substituted to vsie in V=1.
     * Same QEMU limitation as Part A applies here. */
    uintptr_t sie_val = run_in_vs_mode(vs_read_sie, 0);
    TEST_ASSERT("sie.SSIE reflects VSSIE enable via vsie substitution",
                (sie_val & SIP_SSIP) != 0);

    /* Cleanup. */
    CSRW(CSR_HIE, 0);
    hideleg_write(0);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * VSIE-02: hideleg[10]=1 When VSEI is delegated, vsip.SEIP reflects hip.VSEIP.
 * ------------------------------------------------------------------ */
TEST_REGISTER(test_vsie_02);
bool test_vsie_02(void) {
    TEST_BEGIN("VSIE-02: hideleg[10]=1, vsip.SEIP aliases hip.VSEIP");

    /* Delegate VSEI. */
    hideleg_write(HIDELEG_VSEI);

    /* Inject VSEIP via hvip. */
    hvip_set_vsei(true);

    /* VS-mode reads sip.SEIP (bit 9, translated from VSEIP bit 10).
     *
     * Known QEMU limitation: V=1 sip read-direction alias not
     * implemented — VS-mode reading sip returns 0 despite correct
     * M-mode vsip state. See VSIE-01 comment for details. */
    uintptr_t sip_val = run_in_vs_mode(vs_read_sip, 0);
    TEST_ASSERT("sip.SEIP=1 when hideleg[10]=1 and VSEIP pending",
                (sip_val & SIP_SEIP) != 0);

    /* Cleanup. */
    hvip_set_vsei(false);
    hideleg_write(0);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * VSIE-03: hideleg[10]=0 When VSEI is NOT delegated, vsip.SEIP reads as zero regardless
 * of the actual VSEIP state.
 * ------------------------------------------------------------------ */
TEST_REGISTER(test_vsie_03);
bool test_vsie_03(void) {
    TEST_BEGIN("VSIE-03: hideleg[10]=0, vsip.SEIP reads zero");

    /* Do NOT delegate VSEI. */
    hideleg_write(0);

    /* Inject VSEIP via hvip (pending in hip, but not visible to VS). */
    hvip_set_vsei(true);

    /* VS-mode reads sip.SEIP -> should be zero. */
    uintptr_t sip_val = run_in_vs_mode(vs_read_sip, 0);
    TEST_ASSERT("sip.SEIP=0 when hideleg[10]=0 despite VSEIP pending",
                (sip_val & SIP_SEIP) == 0);

    /* Cleanup. */
    hvip_set_vsei(false);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * VSIE-04: hideleg[6]=1 When VSTI is delegated, vsip.STIP reflects hip.VSTIP.
 * ------------------------------------------------------------------ */
TEST_REGISTER(test_vsie_04);
bool test_vsie_04(void) {
    TEST_BEGIN("VSIE-04: hideleg[6]=1, vsip.STIP aliases hip.VSTIP");

    /* Delegate VSTI. */
    hideleg_write(HIDELEG_VSTI);

    /* Inject VSTIP via hvip. */
    hvip_set_vsti(true);

    /* VS-mode reads sip.STIP (bit 5, translated from VSTIP bit 6).
     *
     * Known QEMU limitation: V=1 sip read-direction alias not
     * implemented. See VSIE-01 comment for details. */
    uintptr_t sip_val = run_in_vs_mode(vs_read_sip, 0);
    TEST_ASSERT("sip.STIP=1 when hideleg[6]=1 and VSTIP pending",
                (sip_val & SIP_STIP) != 0);

    /* Cleanup. */
    hvip_set_vsti(false);
    hideleg_write(0);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * VSIE-05: hideleg[6]=0 When VSTI is NOT delegated, vsip.STIP reads as zero.
 * ------------------------------------------------------------------ */
TEST_REGISTER(test_vsie_05);
bool test_vsie_05(void) {
    TEST_BEGIN("VSIE-05: hideleg[6]=0, vsip.STIP reads zero");

    /* Do NOT delegate VSTI. */
    hideleg_write(0);

    /* Inject VSTIP via hvip (pending in hip, but not visible to VS). */
    hvip_set_vsti(true);

    /* VS-mode reads sip.STIP -> should be zero. */
    uintptr_t sip_val = run_in_vs_mode(vs_read_sip, 0);
    TEST_ASSERT("sip.STIP=0 when hideleg[6]=0 despite VSTIP pending",
                (sip_val & SIP_STIP) == 0);

    /* Cleanup. */
    hvip_set_vsti(false);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * VSIE-06: hideleg[2]=1 When VSSI is delegated, vsip.SSIP reflects hip.VSSIP.
 * ------------------------------------------------------------------ */
TEST_REGISTER(test_vsie_06);
bool test_vsie_06(void) {
    TEST_BEGIN("VSIE-06: hideleg[2]=1, vsip.SSIP aliases hip.VSSIP");

    /* Delegate VSSI. */
    hideleg_write(HIDELEG_VSSI);

    /* Inject VSSIP via hvip. */
    hvip_set_vssi(true);

    /* VS-mode reads sip.SSIP (bit 1, translated from VSSIP bit 2).
     *
     * Known QEMU limitation: QEMU does not correctly implement the
     * V=1 sip→vsip read-direction alias. M-mode reading vsip(0x244)
     * returns the correct value, but VS-mode reading sip returns 0.
     * The write direction (VSIE-10) works correctly. */
    uintptr_t sip_val = run_in_vs_mode(vs_read_sip, 0);
    TEST_ASSERT("sip.SSIP=1 when hideleg[2]=1 and VSSIP pending",
                (sip_val & SIP_SSIP) != 0);

    /* Cleanup. */
    hvip_set_vssi(false);
    hideleg_write(0);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * VSIE-07: hideleg[2]=0 When VSSI is NOT delegated, vsip.SSIP reads as zero.
 * ------------------------------------------------------------------ */
TEST_REGISTER(test_vsie_07);
bool test_vsie_07(void) {
    TEST_BEGIN("VSIE-07: hideleg[2]=0, vsip.SSIP reads zero");

    /* Do NOT delegate VSSI. */
    hideleg_write(0);

    /* Inject VSSIP via hvip (pending in hip, but not visible to VS). */
    hvip_set_vssi(true);

    /* VS-mode reads sip.SSIP -> should be zero. */
    uintptr_t sip_val = run_in_vs_mode(vs_read_sip, 0);
    TEST_ASSERT("sip.SSIP=0 when hideleg[2]=0 despite VSSIP pending",
                (sip_val & SIP_SSIP) == 0);

    /* Cleanup. */
    hvip_set_vssi(false);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * VSIE-08: vsie.SEIE alias, When VSEI is delegated, VS-mode writing sie.SEIE updates hie.VSEIE.
 * ------------------------------------------------------------------ */
TEST_REGISTER(test_vsie_08);
bool test_vsie_08(void) {
    TEST_BEGIN("VSIE-08: VS writes sie.SEIE -> hie.VSEIE alias");

    /* Delegate VSEI. */
    hideleg_write(HIDELEG_VSEI);

    /* Clear hie.VSEIE first. */
    CSRC(CSR_HIE, HIE_VSEIE);

    /* VS-mode writes sie.SEIE=1 (substituted to vsie, aliased to hie.VSEIE). */
    run_in_vs_mode(vs_write_sie, SIP_SEIP);

    /* HS-mode reads hie.VSEIE -> should be set. */
    uintptr_t hie_val;
    hie_val = CSRR(CSR_HIE);
    TEST_ASSERT("hie.VSEIE=1 after VS writes sie.SEIE=1",
                (hie_val & HIE_VSEIE) != 0);

    /* Cleanup. */
    CSRC(CSR_HIE, HIE_VSEIE);
    hideleg_write(0);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * VSIE-09: vsie.STIE alias, When VSTI is delegated, VS-mode writing sie.STIE updates hie.VSTIE.
 * ------------------------------------------------------------------ */
TEST_REGISTER(test_vsie_09);
bool test_vsie_09(void) {
    TEST_BEGIN("VSIE-09: VS writes sie.STIE -> hie.VSTIE alias");

    /* Delegate VSTI. */
    hideleg_write(HIDELEG_VSTI);

    /* Clear hie.VSTIE first. */
    CSRC(CSR_HIE, HIE_VSTIE);

    /* VS-mode writes sie.STIE=1. */
    run_in_vs_mode(vs_write_sie, SIP_STIP);

    /* HS-mode reads hie.VSTIE -> should be set. */
    uintptr_t hie_val;
    hie_val = CSRR(CSR_HIE);
    TEST_ASSERT("hie.VSTIE=1 after VS writes sie.STIE=1",
                (hie_val & HIE_VSTIE) != 0);

    /* Cleanup. */
    CSRC(CSR_HIE, HIE_VSTIE);
    hideleg_write(0);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * VSIE-10: vsie.SSIE alias, When VSSI is delegated, VS-mode writing sie.SSIE updates hie.VSSIE.
 * ------------------------------------------------------------------ */
TEST_REGISTER(test_vsie_10);
bool test_vsie_10(void) {
    TEST_BEGIN("VSIE-10: VS writes sie.SSIE -> hie.VSSIE alias");

    /* Delegate VSSI. */
    hideleg_write(HIDELEG_VSSI);

    /* Clear hie.VSSIE first. */
    CSRC(CSR_HIE, HIE_VSSIE);

    /* VS-mode writes sie.SSIE=1. */
    run_in_vs_mode(vs_write_sie, SIP_SSIP);

    /* HS-mode reads hie.VSSIE -> should be set. */
    uintptr_t hie_val;
    hie_val = CSRR(CSR_HIE);
    TEST_ASSERT("hie.VSSIE=1 after VS writes sie.SSIE=1",
                (hie_val & HIE_VSSIE) != 0);

    /* Cleanup. */
    CSRC(CSR_HIE, HIE_VSSIE);
    hideleg_write(0);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * Helper: neutralize all VS interrupt sources before entering VS-mode.
 *
 * Previous test groups (Group 4/10) may leave:
 *   - mideleg bits set (e.g. mideleg[5] for STI delegation)
 *   - VSTIP pending in hip (from vstimecmp-based tests)
 *   - mstatus.MPIE=1 (from interrupt delivery tests)
 *
 * These residual states can cause real interrupts when entering
 * VS-mode with hie enable bits set, leading to infinite trap loops.
 * The M-mode trap handler clears stimecmp(0x14D) for irq=5, but
 * that does NOT clear VSTIP (which requires vstimecmp(0x24D)).
 *
 * This helper comprehensively neutralizes all sources:
 *   1. Clear mideleg[1,5,9] — prevent STI/SSI/SEI delegation to S
 *   2. Clear MPIE — ensure MIE=0 after mret to VS-mode
 *   3. Clear hvip — remove software-injected pending ints
 *   4. Set vstimecmp to max — prevent VSTIP from timer comparison
 * ------------------------------------------------------------------ */
static void neutralize_vs_int_sources(void) {
    /* 1. Clear mideleg for S-level interrupt delegation.
     *    Prevents VSTIP/VSSIP/VSEIP (via hip->mip chain) from being
     *    forwarded to S-mode when entering VS-mode. mideleg is M-level
     *    config; clear the bits via the adaptive wrapper (proxies to M
     *    from S(HS)-mode). */
    tsbi_csr_clear(CSR_MIDELEG, (1UL << 5) | (1UL << 9) | (1UL << 1));

    /* 2. Clear mie.STIE/SEIE/SSIE — disable M-mode S-level interrupt
     *    enables. Even if mip.STIP remains pending, the interrupt
     *    cannot fire without mie enable. mie is M-level config. */
    tsbi_csr_clear(CSR_MIE, (1UL << 5) | (1UL << 9) | (1UL << 1));

    /* 3. (removed) The old code cleared mstatus.MPIE so that "MIE=0 after
     *    mret into VS-mode". Under the S-mode-normal + T-SBI model this is
     *    both unimplementable and unnecessary. Unimplementable: MPIE is a
     *    return-path bit the tsbi_csr_ guard refuses to proxy, and every framework
     *    excursion re-enters via mret (which sets MPIE<-1). Unnecessary:
     *    mstatus.MIE only gates interrupts while executing IN M-mode; in
     *    VS-mode (privilege < M) M-interrupts are always globally enabled, so
     *    MIE=0 never quiesced the guest. The real quiescing is steps 1/2/4/5
     *    (mideleg, mie, hvip, vstimecmp); VS-level delivery is gated by
     *    vsstatus.SIE, which the guest itself owns. */

    /* 4. Clear all hvip bits (removes software-injected pending). */
    CSRW(CSR_HVIP, 0);

    /* 5. Set vstimecmp (0x24D) to max to prevent VSTIP from timer. */
    CSRW(CSR_VSTIMECMP, (uintptr_t)-1);

    /* 6. Verify VSTIP cleared in hip. If still pending (Spike timer
     *    quirk), poll with timeout. The re-write inside the loop
     *    handles platforms with delayed comparison evaluation. */
    uintptr_t hip_val;
    int retry = 10000;
    do {
        hip_val = CSRR(CSR_HIP);
        if (!(hip_val & (1UL << 6))) break;
        CSRW(CSR_VSTIMECMP, (uintptr_t)-1);
    } while (--retry > 0);
}

/* ------------------------------------------------------------------
 * VSIE-11: hideleg[10]=0, vsie.SEIE reads as zero (read-only zero).
 * Even if hie.VSEIE=1, VS-mode reading sie.SEIE must see 0.
 * ------------------------------------------------------------------ */
TEST_REGISTER(test_vsie_11);
bool test_vsie_11(void) {
    TEST_BEGIN("VSIE-11: hideleg[10]=0, vsie.SEIE reads zero");

    /* Do NOT delegate VSEI. */
    hideleg_write(0);
    neutralize_vs_int_sources();

    /* Set hie.VSEIE so the backing register has the bit set. */
    CSRS(CSR_HIE, HIE_VSEIE);

    /* VS-mode reads sie.SEIE (bit 9) -> must be 0. */
    uintptr_t sie_val = run_in_vs_mode(vs_read_sie, 0);
    TEST_ASSERT("sie.SEIE=0 when hideleg[10]=0 despite hie.VSEIE=1",
                (sie_val & SIP_SEIP) == 0);

    /* Cleanup. */
    CSRC(CSR_HIE, HIE_VSEIE);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * VSIE-12: hideleg[6]=0, vsie.STIE reads as zero (read-only zero).
 *
 * Uses M-mode direct read of vsie (CSR 0x204) to avoid Spike timer
 * interaction issues during VS-mode entry. When VSTIP is pending
 * from previous vstimecmp tests, entering VS-mode with hie.VSTIE
 * set can trigger infinite M-mode trap loops on Spike (whose M-mode
 * trap handler clears stimecmp(0x14D) but not vstimecmp(0x24D)).
 * M-mode direct access is equivalent: the spec defines vsie.STIE
 * as read-only zero when hideleg[6]=0, regardless of access mode.
 * ------------------------------------------------------------------ */
TEST_REGISTER(test_vsie_12);
bool test_vsie_12(void) {
    TEST_BEGIN("VSIE-12: hideleg[6]=0, vsie.STIE reads zero");

    hideleg_write(0);

    /* Set hie.VSTIE so the backing register has the bit set. */
    CSRS(CSR_HIE, HIE_VSTIE);

    /* M-mode reads vsie directly (CSR 0x204).
     * vsie.STIE (bit 5) must be 0 when hideleg[6]=0. */
    uintptr_t vsie_val = vsie_read();
    TEST_ASSERT("vsie.STIE=0 when hideleg[6]=0 despite hie.VSTIE=1",
                (vsie_val & SIP_STIP) == 0);

    /* Cleanup. */
    CSRC(CSR_HIE, HIE_VSTIE);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * VSIE-13: hideleg[2]=0, vsie.SSIE reads as zero (read-only zero).
 * ------------------------------------------------------------------ */
TEST_REGISTER(test_vsie_13);
bool test_vsie_13(void) {
    TEST_BEGIN("VSIE-13: hideleg[2]=0, vsie.SSIE reads zero");

    hideleg_write(0);
    neutralize_vs_int_sources();

    /* Set hie.VSSIE. */
    CSRS(CSR_HIE, HIE_VSSIE);

    /* VS-mode reads sie.SSIE (bit 1) -> must be 0. */
    uintptr_t sie_val = run_in_vs_mode(vs_read_sie, 0);
    TEST_ASSERT("sie.SSIE=0 when hideleg[2]=0 despite hie.VSSIE=1",
                (sie_val & SIP_SSIP) == 0);

    /* Cleanup. */
    CSRC(CSR_HIE, HIE_VSSIE);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * VSIE-14: hideleg[10]=0, VS writes sie.SEIE=1 -> hie.VSEIE unchanged.
 * Verifies write direction WARL: vsie.SEIE is read-only zero when
 * hideleg[10]=0, so writes must have no effect on the alias target.
 * ------------------------------------------------------------------ */
TEST_REGISTER(test_vsie_14);
bool test_vsie_14(void) {
    TEST_BEGIN("VSIE-14: hideleg[10]=0, VS write sie.SEIE no effect");

    hideleg_write(0);
    neutralize_vs_int_sources();

    /* Clear hie first. */
    CSRW(CSR_HIE, 0);

    /* VS-mode writes sie.SEIE=1 -> should be silently ignored. */
    run_in_vs_mode(vs_write_sie, SIP_SEIP);

    /* HS-mode reads hie.VSEIE -> must remain 0. */
    uintptr_t hie_val;
    hie_val = CSRR(CSR_HIE);
    TEST_ASSERT("hie.VSEIE=0 after VS write sie.SEIE with hideleg[10]=0",
                (hie_val & HIE_VSEIE) == 0);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * VSIE-15: hideleg[6]=0, VS writes sie.STIE=1 -> hie.VSTIE unchanged.
 * ------------------------------------------------------------------ */
TEST_REGISTER(test_vsie_15);
bool test_vsie_15(void) {
    TEST_BEGIN("VSIE-15: hideleg[6]=0, VS write sie.STIE no effect");

    hideleg_write(0);
    neutralize_vs_int_sources();
    CSRW(CSR_HIE, 0);

    run_in_vs_mode(vs_write_sie, SIP_STIP);

    uintptr_t hie_val;
    hie_val = CSRR(CSR_HIE);
    TEST_ASSERT("hie.VSTIE=0 after VS write sie.STIE with hideleg[6]=0",
                (hie_val & HIE_VSTIE) == 0);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * VSIE-16: hideleg[2]=0, VS writes sie.SSIE=1 -> hie.VSSIE unchanged.
 * ------------------------------------------------------------------ */
TEST_REGISTER(test_vsie_16);
bool test_vsie_16(void) {
    TEST_BEGIN("VSIE-16: hideleg[2]=0, VS write sie.SSIE no effect");

    hideleg_write(0);
    neutralize_vs_int_sources();
    CSRW(CSR_HIE, 0);

    run_in_vs_mode(vs_write_sie, SIP_SSIP);

    uintptr_t hie_val;
    hie_val = CSRR(CSR_HIE);
    TEST_ASSERT("hie.VSSIE=0 after VS write sie.SSIE with hideleg[2]=0",
                (hie_val & HIE_VSSIE) == 0);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * VSIE-17: vsie (CSR 0x204) is a read/write register.
 * M-mode writes vsie directly, reads back to verify R/W behavior.
 * ------------------------------------------------------------------ */
TEST_REGISTER(test_vsie_17);
bool test_vsie_17(void) {
    TEST_BEGIN("VSIE-17: vsie direct CSR read/write");

    /* Delegate all three standard VS interrupts so that the alias
     * bits in vsie (SEIE/STIE/SSIE) become writable. When hideleg
     * bits are zero, those positions are read-only zero in vsie. */
    hideleg_write(HIDELEG_VSEI | HIDELEG_VSTI | HIDELEG_VSSI);

    /* Save and clear. */
    uintptr_t saved = vsie_read();
    vsie_write(0);

    /* Write a pattern (SEIE | STIE | SSIE bits in S-mode encoding). */
    uintptr_t pattern = SIP_SEIP | SIP_STIP | SIP_SSIP;
    vsie_write(pattern);
    uintptr_t readback = vsie_read();

    /* At minimum, the three standard interrupt enable bits must be
     * writable. Other bits (LCOFIE etc.) are implementation-dependent. */
    TEST_ASSERT("vsie readback matches written SEIE|STIE|SSIE pattern",
                (readback & pattern) == pattern);

    /* Restore. */
    vsie_write(saved);
    hideleg_write(0);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * VSIE-18: vsip.SSIP (bit 1) is writable from M-mode (CSR 0x244).
 * vsip.SSIP aliases hvip.VSSIP when hideleg[2]=1. Writing vsip.SSIP
 * from M-mode should set the pending bit visible in vsip read-back.
 * ------------------------------------------------------------------ */
TEST_REGISTER(test_vsie_18);
bool test_vsie_18(void) {
    TEST_BEGIN("VSIE-18: vsip.SSIP writable from M-mode");

    /* Delegate VSSI so vsip.SSIP is backed by hvip.VSSIP. */
    hideleg_write(HIDELEG_VSSI);

    /* Clear hvip.VSSIP first. */
    hvip_set_vssi(false);

    /* Write vsip.SSIP=1 from M-mode. */
    vsip_write(SIP_SSIP);

    /* Read back vsip -> SSIP should be set. */
    uintptr_t vsip_val = vsip_read();
    TEST_ASSERT("vsip.SSIP=1 after M-mode write",
                (vsip_val & SIP_SSIP) != 0);

    /* Cleanup. */
    hvip_set_vssi(false);
    hideleg_write(0);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * VSIE-19: vsip alias chain verification (hideleg[2]=1).
 * hvip.VSSIP=1 -> M-mode reads vsip(0x244) -> bit 1 (SSIP) is set.
 * Confirms the alias is visible from HS/M-mode, not just VS-mode.
 * ------------------------------------------------------------------ */
TEST_REGISTER(test_vsie_19);
bool test_vsie_19(void) {
    TEST_BEGIN("VSIE-19: vsip alias chain, M-mode reads vsip.SSIP");

    hideleg_write(HIDELEG_VSSI);
    hvip_set_vssi(true);

    uintptr_t vsip_val = vsip_read();
    TEST_ASSERT("vsip.SSIP=1 when hvip.VSSIP=1 and hideleg[2]=1",
                (vsip_val & SIP_SSIP) != 0);

    hvip_set_vssi(false);
    hideleg_write(0);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * VSIE-20: vsip alias chain verification for SEI (hideleg[10]=1).
 * hvip.VSEIP=1 -> M-mode reads vsip(0x244) -> bit 9 (SEIP) is set.
 * Note the bit translation: VSEIP is bit 10 in hip/hvip, but SEIP
 * is bit 9 in vsip/sip.
 * ------------------------------------------------------------------ */
TEST_REGISTER(test_vsie_20);
bool test_vsie_20(void) {
    TEST_BEGIN("VSIE-20: vsip alias chain, M-mode reads vsip.SEIP");

    hideleg_write(HIDELEG_VSEI);
    hvip_set_vsei(true);

    uintptr_t vsip_val = vsip_read();
    TEST_ASSERT("vsip.SEIP=1 when hvip.VSEIP=1 and hideleg[10]=1",
                (vsip_val & SIP_SEIP) != 0);

    hvip_set_vsei(false);
    hideleg_write(0);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * VSIE-21: hideleg[13] writability probe (Shlcofideleg extension).
 * Per norm:vsip_vsie_lcofi, if Shlcofideleg is implemented, hideleg
 * bit 13 is writable; otherwise it is read-only zero.
 * ------------------------------------------------------------------ */
TEST_REGISTER(test_vsie_21);
bool test_vsie_21(void) {
    TEST_BEGIN("VSIE-21: hideleg[13] LCOFI writability probe");

    /* Save original hideleg. */
    uintptr_t saved = hideleg_read();

    /* Try to set bit 13. */
    hideleg_write(saved | (1UL << 13));
    uintptr_t readback = hideleg_read();
    bool lcofi_deleg_supported = ((readback & (1UL << 13)) != 0);

    /* Restore. */
    hideleg_write(saved);

    /* Report: this is an informational probe. If bit 13 sticks,
     * Shlcofideleg is implemented. The test always passes; the result
     * is recorded in the assertion message for diagnostic purposes. */
    if (lcofi_deleg_supported) {
        TEST_ASSERT("hideleg[13] writable: Shlcofideleg implemented",
                    true);
    } else {
        TEST_ASSERT("hideleg[13] read-only zero: Shlcofideleg not implemented",
                    true);
    }

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * VSIE-22: hideleg[13]=0, vsip.LCOFIP and vsie.LCOFIE read-only zero.
 * Per norm:vsip_vsie_lcofi, when hideleg bit 13 is zero, both
 * vsip.LCOFIP (bit 13) and vsie.LCOFIE (bit 13) must read as zero
 * regardless of the underlying sip/mip state.
 * ------------------------------------------------------------------ */
TEST_REGISTER(test_vsie_22);
bool test_vsie_22(void) {
    TEST_BEGIN("VSIE-22: hideleg[13]=0, vsip/vsie LCOFI read-only zero");

    /* First check if Shlcofideleg is implemented at all. */
    uintptr_t saved_hideleg = hideleg_read();
    hideleg_write(saved_hideleg | MIP_LCOFIP);
    bool lcofi_supported = ((hideleg_read() & MIP_LCOFIP) != 0);
    hideleg_write(saved_hideleg);

    if (!lcofi_supported) {
        /* If Shlcofideleg is not implemented, LCOFI bits are always
         * zero in vsip/vsie regardless of hideleg. Verify this. */
        uintptr_t vsip_val = vsip_read();
        uintptr_t vsie_val = vsie_read();
        TEST_ASSERT("vsip.LCOFIP=0 when Shlcofideleg not implemented",
                    (vsip_val & MIP_LCOFIP) == 0);
        TEST_ASSERT("vsie.LCOFIE=0 when Shlcofideleg not implemented",
                    (vsie_val & MIP_LCOFIP) == 0);
    } else {
        /* Shlcofideleg is implemented. Clear hideleg[13] and verify
         * vsip.LCOFIP and vsie.LCOFIE are read-only zero. */
        hideleg_write(saved_hideleg & ~MIP_LCOFIP);

        /* Try to set vsie.LCOFIE from M-mode. */
        uintptr_t saved_vsie = vsie_read();
        vsie_write(saved_vsie | MIP_LCOFIP);

        /* Read vsie from M-mode. */
        uintptr_t vsie_val = vsie_read();
        TEST_ASSERT("vsie.LCOFIE=0 when hideleg[13]=0",
                    (vsie_val & MIP_LCOFIP) == 0);

        /* Read vsip from M-mode. */
        uintptr_t vsip_val = vsip_read();
        TEST_ASSERT("vsip.LCOFIP=0 when hideleg[13]=0",
                    (vsip_val & MIP_LCOFIP) == 0);

        /* Restore. */
        vsie_write(saved_vsie);
        hideleg_write(saved_hideleg);
    }

    HYP_TEST_END();
}
