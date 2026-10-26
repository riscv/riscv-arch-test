/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * Test Group 3: mideleg/mip/mie enhancements
 *
 * Tests MIDLG-01 through MIDLG-07 verify delegation and interrupt enhancements.
 *
 * SPEC references:
 *   norm:mideleg_acc_h  - mideleg bits 10/6/2 read-only 1;
 *                         bit 12 read-only 1 when GEILEN>0
 *   norm:mideleg_hroz   - for mideleg=0 bits, corresponding
 *                         hideleg/hip/hie bits are read-only zeros
 *   norm:mip_mie_vs     - mip/mie have additional active VS bits
 *   norm:mip_mie_alias  - SGEIP/VSEIP/VSTIP/VSSIP in mip alias hip;
 *                         SGEIE/VSEIE/VSTIE/VSSIE in mie alias hie
 */

#include "hyp_test_helpers.h"

/* VS / SGE interrupt bit positions (shared by mip/mie/hip/hie). */
#define VS_BIT_VSSI   (1UL << 2)
#define VS_BIT_VSTI   (1UL << 6)
#define VS_BIT_VSEI   (1UL << 10)
#define VS_BIT_SGEI   (1UL << 12)
#define VS_ALL_BITS   (VS_BIT_VSSI | VS_BIT_VSTI | VS_BIT_VSEI | VS_BIT_SGEI)

/* ------------------------------------------------------------------
 * MIDLG-01: mideleg bits 10/6/2 read-only 1
 *
 * SPEC norm:mideleg_acc_h: bits 10, 6, and 2 of mideleg are each
 * read-only one when the hypervisor extension is implemented.
 * ------------------------------------------------------------------ */
TEST_REGISTER(mideleg_readonly_bits);
bool mideleg_readonly_bits(void)
{
    TEST_BEGIN("MIDLG-01: Verify mideleg bits 10/6/2 are read-only 1");

    /* Read mideleg (M-level config; via the T-SBI proxy). */
    uintptr_t val = tsbi_csr_read(CSR_MIDELEG);

    /* Verify bits 10, 6, 2 are 1. */
    uintptr_t mask = VS_BIT_VSEI | VS_BIT_VSTI | VS_BIT_VSSI;
    TEST_ASSERT_EQ("mideleg bits 10/6/2 should be 1", val & mask, mask);

    /* Try to clear these bits. */
    val &= ~mask;
    tsbi_csr_write(CSR_MIDELEG, val);

    /* Read back and verify they are still 1. */
    val = tsbi_csr_read(CSR_MIDELEG);
    TEST_ASSERT_EQ("mideleg bits 10/6/2 should still be 1 after clear attempt",
                   val & mask, mask);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * MIDLG-02: mideleg bit 12 read-only 1 (GEILEN>0)
 *
 * SPEC norm:mideleg_acc_h: if GEILEN is nonzero, bit 12 of mideleg
 * is read-only one.  We detect GEILEN by writing all-ones to hgeie
 * and reading back.
 * ------------------------------------------------------------------ */
TEST_REGISTER(mideleg_bit12_geilen);
bool mideleg_bit12_geilen(void)
{
    TEST_BEGIN("MIDLG-02: Verify mideleg bit 12 read-only 1 when GEILEN>0");

    /* Detect GEILEN: write all 1s to hgeie and read back. */
    CSRW(CSR_HGEIE, (uintptr_t)-1);
    uintptr_t hgeie;
    hgeie = CSRR(CSR_HGEIE);
    /* Restore hgeie to 0 to avoid spurious guest external interrupts. */
    CSRW(CSR_HGEIE, 0);

    if (hgeie == 0)
    {
        TEST_SKIP("GEILEN=0 (hgeie reads zero), bit 12 not required to be RO1");
    }

    /* GEILEN>0: read mideleg and verify bit 12 is 1 (M-level config; via the
     * the T-SBI proxy). */
    uintptr_t val = tsbi_csr_read(CSR_MIDELEG);
    TEST_ASSERT_EQ("mideleg bit 12 should be 1 when GEILEN>0",
                   val & VS_BIT_SGEI, VS_BIT_SGEI);

    /* Attempt to clear bit 12 and verify it remains 1. */
    val &= ~VS_BIT_SGEI;
    tsbi_csr_write(CSR_MIDELEG, val);

    val = tsbi_csr_read(CSR_MIDELEG);
    TEST_ASSERT_EQ("mideleg bit 12 should still be 1 after clear attempt",
                   val & VS_BIT_SGEI, VS_BIT_SGEI);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * MIDLG-03: hideleg/hip/hie read-only zero for mideleg=0 bits
 *
 * SPEC norm:mideleg_hroz: for bits of mideleg that are zero, the
 * corresponding bits in hideleg, hip, and hie are read-only zeros.
 * ------------------------------------------------------------------ */
TEST_REGISTER(hideleg_readonly_zero);
bool hideleg_readonly_zero(void)
{
    TEST_BEGIN("MIDLG-03: Verify hideleg/hip/hie bits RO-zero when mideleg=0");

    uintptr_t mideleg = tsbi_csr_read(CSR_MIDELEG);

    /*
     * Find a writable candidate bit: scan bits [15:0] excluding the
     * always-delegated VS bits (10/6/2) and SGEI (12).  We look for
     * a bit that is currently 0 in mideleg.
     */
    uintptr_t exclude = VS_BIT_VSSI | VS_BIT_VSTI | VS_BIT_VSEI | VS_BIT_SGEI;
    uintptr_t candidate = 0;
    for (int i = 0; i < 16; i++)
    {
        uintptr_t b = 1UL << i;
        if ((b & exclude) == 0 && (mideleg & b) == 0)
        {
            candidate = b;
            break;
        }
    }

    if (candidate == 0)
    {
        TEST_SKIP("No mideleg=0 candidate bit found in [15:0]");
    }

    /* --- hideleg: attempt to set the candidate bit, expect read-only 0 --- */
    uintptr_t hideleg;
    hideleg = CSRR(CSR_HIDELEG);
    hideleg |= candidate;
    CSRW(CSR_HIDELEG, hideleg);
    hideleg = CSRR(CSR_HIDELEG);
    TEST_ASSERT_EQ("hideleg bit should read-zero when mideleg bit=0",
                   hideleg & candidate, (uintptr_t)0);

    /* --- hip: attempt to set the candidate bit, expect read-only 0 --- */
    uintptr_t hip;
    hip = CSRR(CSR_HIP);
    hip |= candidate;
    CSRW(CSR_HIP, hip);
    hip = CSRR(CSR_HIP);
    TEST_ASSERT_EQ("hip bit should read-zero when mideleg bit=0",
                   hip & candidate, (uintptr_t)0);

    /* --- hie: attempt to set the candidate bit, expect read-only 0 --- */
    uintptr_t hie;
    hie = CSRR(CSR_HIE);
    hie |= candidate;
    CSRW(CSR_HIE, hie);
    hie = CSRR(CSR_HIE);
    TEST_ASSERT_EQ("hie bit should read-zero when mideleg bit=0",
                   hie & candidate, (uintptr_t)0);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * MIDLG-04: mip VS interrupt bits are hip aliases (VSSIP/VSTIP/VSEIP)
 *
 * SPEC norm:mip_mie_alias: VSEIP, VSTIP, and VSSIP in mip are
 * aliases for the same bits in hip.
 * ------------------------------------------------------------------ */
TEST_REGISTER(mip_vSSIP_alias);
bool mip_vSSIP_alias(void)
{
    TEST_BEGIN("MIDLG-04: Verify mip VSSIP/VSTIP/VSEIP are hip aliases");

    /* ---- VSSIP (bit 2): set via hvip, verify mip reflects it ---- */
    hvip_set_vssi(true);

    uintptr_t mip, hip;
    mip = tsbi_csr_read(CSR_MIP);
    hip = CSRR(CSR_HIP);
    TEST_ASSERT_EQ("mip.VSSIP should be 1 when hvip.VSSI set",
                   mip & VS_BIT_VSSI, VS_BIT_VSSI);
    TEST_ASSERT_EQ("hip.VSSIP should be 1 when hvip.VSSI set",
                   hip & VS_BIT_VSSI, VS_BIT_VSSI);

    hvip_set_vssi(false);
    mip = tsbi_csr_read(CSR_MIP);
    hip = CSRR(CSR_HIP);
    TEST_ASSERT_EQ("mip.VSSIP should be 0 when hvip.VSSI cleared",
                   mip & VS_BIT_VSSI, (uintptr_t)0);
    TEST_ASSERT_EQ("hip.VSSIP should be 0 when hvip.VSSI cleared",
                   hip & VS_BIT_VSSI, (uintptr_t)0);

    /* ---- VSTIP (bit 6): set via hvip, verify mip reflects it ---- */
    hvip_set_vsti(true);

    mip = tsbi_csr_read(CSR_MIP);
    hip = CSRR(CSR_HIP);
    TEST_ASSERT_EQ("mip.VSTIP should be 1 when hvip.VSTI set",
                   mip & VS_BIT_VSTI, VS_BIT_VSTI);
    TEST_ASSERT_EQ("hip.VSTIP should be 1 when hvip.VSTI set",
                   hip & VS_BIT_VSTI, VS_BIT_VSTI);

    hvip_set_vsti(false);
    mip = tsbi_csr_read(CSR_MIP);
    hip = CSRR(CSR_HIP);
    TEST_ASSERT_EQ("mip.VSTIP should be 0 when hvip.VSTI cleared",
                   mip & VS_BIT_VSTI, (uintptr_t)0);
    TEST_ASSERT_EQ("hip.VSTIP should be 0 when hvip.VSTI cleared",
                   hip & VS_BIT_VSTI, (uintptr_t)0);

    /* ---- VSEIP (bit 10): set via hvip, verify mip reflects it ---- */
    hvip_set_vsei(true);

    mip = tsbi_csr_read(CSR_MIP);
    hip = CSRR(CSR_HIP);
    TEST_ASSERT_EQ("mip.VSEIP should be 1 when hvip.VSEI set",
                   mip & VS_BIT_VSEI, VS_BIT_VSEI);
    TEST_ASSERT_EQ("hip.VSEIP should be 1 when hvip.VSEI set",
                   hip & VS_BIT_VSEI, VS_BIT_VSEI);

    hvip_set_vsei(false);
    mip = tsbi_csr_read(CSR_MIP);
    hip = CSRR(CSR_HIP);
    TEST_ASSERT_EQ("mip.VSEIP should be 0 when hvip.VSEI cleared",
                   mip & VS_BIT_VSEI, (uintptr_t)0);
    TEST_ASSERT_EQ("hip.VSEIP should be 0 when hvip.VSEI cleared",
                   hip & VS_BIT_VSEI, (uintptr_t)0);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * MIDLG-05: mip SGEIP is hip.SGEIP alias (GEILEN>0)
 *
 * SPEC norm:mip_mie_alias: SGEIP in mip is an alias for the same
 * bit in hip.  This test verifies the alias relationship when
 * guest external interrupts are implemented.
 * ------------------------------------------------------------------ */
TEST_REGISTER(mip_vSEIP_alias);
bool mip_vSEIP_alias(void)
{
    TEST_BEGIN("MIDLG-05: Verify mip SGEIP is hip.SGEIP alias");

    /* Detect GEILEN to see if SGEIP is supported. */
    CSRW(CSR_HGEIE, (uintptr_t)-1);
    uintptr_t hgeie;
    hgeie = CSRR(CSR_HGEIE);
    CSRW(CSR_HGEIE, 0);

    if (hgeie == 0)
    {
        TEST_SKIP("GEILEN=0, SGEIP not implemented");
    }

    /*
     * SGEIP (bit 12) in mip/hip is the OR of all active guest external
     * interrupts.  We cannot directly set it via hvip; instead we verify
     * the alias by reading both mip and hip and confirming they match
     * on bit 12.
     */
    uintptr_t mip, hip;
    mip = tsbi_csr_read(CSR_MIP);
    hip = CSRR(CSR_HIP);
    TEST_ASSERT_EQ("mip.SGEIP should equal hip.SGEIP (alias)",
                   mip & VS_BIT_SGEI, hip & VS_BIT_SGEI);

    /*
     * Enable a guest external interrupt source via hgeie and verify
     * that mip.SGEIP and hip.SGEIP remain consistent.
     */
    CSRW(CSR_HGEIE, 1UL);
    mip = tsbi_csr_read(CSR_MIP);
    hip = CSRR(CSR_HIP);
    TEST_ASSERT_EQ("mip.SGEIP should equal hip.SGEIP after hgeie write",
                   mip & VS_BIT_SGEI, hip & VS_BIT_SGEI);
    /* Restore hgeie. */
    CSRW(CSR_HGEIE, 0);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * MIDLG-06: mie VS/SGE enable bits are hie aliases
 *
 * SPEC norm:mip_mie_alias: SGEIE, VSEIE, VSTIE, and VSSIE in mie
 * are aliases for the same bits in hie.
 * ------------------------------------------------------------------ */
TEST_REGISTER(mie_vSSIE_alias);
bool mie_vSSIE_alias(void)
{
    TEST_BEGIN("MIDLG-06: Verify mie VSSIE/VSTIE/VSEIE/SGEIE are hie aliases");

    /* Save original hie and clear it. */
    uintptr_t hie_orig;
    hie_orig = CSRR(CSR_HIE);
    CSRW(CSR_HIE, 0);

    uintptr_t hie, mie_val;

    /* ---- VSSIE (bit 2): set via hie, verify mie reflects it ---- */
    CSRS(CSR_HIE, VS_BIT_VSSI);
    hie = CSRR(CSR_HIE);
    mie_val = tsbi_csr_read(CSR_MIE);
    TEST_ASSERT_EQ("hie.VSSIE should be 1",
                   hie & VS_BIT_VSSI, VS_BIT_VSSI);
    TEST_ASSERT_EQ("mie.VSSIE should be 1 when hie.VSSIE set",
                   mie_val & VS_BIT_VSSI, VS_BIT_VSSI);
    CSRC(CSR_HIE, VS_BIT_VSSI);
    mie_val = tsbi_csr_read(CSR_MIE);
    TEST_ASSERT_EQ("mie.VSSIE should be 0 when hie.VSSIE cleared",
                   mie_val & VS_BIT_VSSI, (uintptr_t)0);

    /* ---- VSTIE (bit 6): set via hie, verify mie reflects it ---- */
    CSRS(CSR_HIE, VS_BIT_VSTI);
    hie = CSRR(CSR_HIE);
    mie_val = tsbi_csr_read(CSR_MIE);
    TEST_ASSERT_EQ("hie.VSTIE should be 1",
                   hie & VS_BIT_VSTI, VS_BIT_VSTI);
    TEST_ASSERT_EQ("mie.VSTIE should be 1 when hie.VSTIE set",
                   mie_val & VS_BIT_VSTI, VS_BIT_VSTI);
    CSRC(CSR_HIE, VS_BIT_VSTI);
    mie_val = tsbi_csr_read(CSR_MIE);
    TEST_ASSERT_EQ("mie.VSTIE should be 0 when hie.VSTIE cleared",
                   mie_val & VS_BIT_VSTI, (uintptr_t)0);

    /* ---- VSEIE (bit 10): set via hie, verify mie reflects it ---- */
    CSRS(CSR_HIE, VS_BIT_VSEI);
    hie = CSRR(CSR_HIE);
    mie_val = tsbi_csr_read(CSR_MIE);
    TEST_ASSERT_EQ("hie.VSEIE should be 1",
                   hie & VS_BIT_VSEI, VS_BIT_VSEI);
    TEST_ASSERT_EQ("mie.VSEIE should be 1 when hie.VSEIE set",
                   mie_val & VS_BIT_VSEI, VS_BIT_VSEI);
    CSRC(CSR_HIE, VS_BIT_VSEI);
    mie_val = tsbi_csr_read(CSR_MIE);
    TEST_ASSERT_EQ("mie.VSEIE should be 0 when hie.VSEIE cleared",
                   mie_val & VS_BIT_VSEI, (uintptr_t)0);

    /* ---- SGEIE (bit 12): set via hie, verify mie reflects it ---- */
    CSRS(CSR_HIE, VS_BIT_SGEI);
    hie = CSRR(CSR_HIE);
    mie_val = tsbi_csr_read(CSR_MIE);
    /*
     * SGEIE in hie is read-only 0 when GEILEN=0.  Check if it stuck.
     */
    if (hie & VS_BIT_SGEI)
    {
        TEST_ASSERT_EQ("mie.SGEIE should be 1 when hie.SGEIE set",
                       mie_val & VS_BIT_SGEI, VS_BIT_SGEI);
        CSRC(CSR_HIE, VS_BIT_SGEI);
        mie_val = tsbi_csr_read(CSR_MIE);
        TEST_ASSERT_EQ("mie.SGEIE should be 0 when hie.SGEIE cleared",
                       mie_val & VS_BIT_SGEI, (uintptr_t)0);
    }
    else
    {
        TEST_SKIP("hgeie=0 or GEILEN=0, SGEIE is read-only 0 in hie");
    }

    /* Restore original hie. */
    CSRW(CSR_HIE, hie_orig);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * MIDLG-07: mip/mie VS interrupt bits are writable/active
 *
 * SPEC norm:mip_mie_vs: the hypervisor extension gives registers
 * mip and mie additional active bits for the hypervisor-added
 * interrupts.  We verify mie VS enable bits are writable and
 * read back correctly.
 * ------------------------------------------------------------------ */
TEST_REGISTER(mip_mie_vs_bits_visible);
bool mip_mie_vs_bits_visible(void)
{
    TEST_BEGIN("MIDLG-07: Verify mip/mie VS interrupt bits are active");

    /* Save original mie (M-level config; via the T-SBI proxy). */
    uintptr_t mie_orig = tsbi_csr_read(CSR_MIE);

    /*
     * VS enable bits: VSSIE(2), VSTIE(6), VSEIE(10).
     * SGEIE(12) may be RO0 when GEILEN=0, so we test it separately.
     */
    uintptr_t vs_enable = VS_BIT_VSSI | VS_BIT_VSTI | VS_BIT_VSEI;

    /* Write all VS enable bits to mie (M-level; via the T-SBI proxy). */
    tsbi_csr_set(CSR_MIE, vs_enable);

    /* Read back and verify all three bits stuck. */
    uintptr_t mie_val;
    mie_val = tsbi_csr_read(CSR_MIE);
    TEST_ASSERT_EQ("mie VS enable bits should be writable",
                   mie_val & vs_enable, vs_enable);

    /* Clear all VS enable bits. */
    tsbi_csr_clear(CSR_MIE, vs_enable);
    mie_val = tsbi_csr_read(CSR_MIE);
    TEST_ASSERT_EQ("mie VS enable bits should be clearable",
                   mie_val & vs_enable, (uintptr_t)0);

    /*
     * Verify mip VS bits (2/6/10) are readable.  These reflect
     * current pending state so we just confirm the bit positions
     * are not hardwired to zero (i.e., the field exists).
     * We set hvip to inject VSSI and check mip bit 2.
     */
    hvip_set_vssi(true);
    uintptr_t mip;
    mip = tsbi_csr_read(CSR_MIP);
    TEST_ASSERT_EQ("mip.VSSIP should be readable and reflect hvip",
                   mip & VS_BIT_VSSI, VS_BIT_VSSI);
    hvip_set_vssi(false);

    /* Restore original mie. */
    tsbi_csr_write(CSR_MIE, mie_orig);

    HYP_TEST_END();
}
