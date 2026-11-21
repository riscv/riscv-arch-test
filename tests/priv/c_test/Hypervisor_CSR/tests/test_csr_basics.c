/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_csr_basics.c - Group 1: VCSR - VS CSR Substitution
 *
 * Tests VCSR-01 through VCSR-17
 * Validates V=1 CSR substitution mechanism:
 *  - VS CSRs are accessible from M/HS-mode by their direct addresses
 *  - S-level CSR accesses transparently map to VS counterparts when V=1
 *  - Direct VS CSR address access from VS/VU-mode triggers exceptions
 *  - CSRs without VS counterparts (senvcfg, scounteren) are unaffected
 */

#include "hyp_test_helpers.h"

/* Sstatus writable bits used in substitution tests. */
#define SSTATUS_SPIE  (1UL << 5)

/* Test value covering common writable sstatus/vsstatus bits. */
#define VSSTATUS_TEST_VAL  (SSTATUS_SPIE | SSTATUS_MXR_BIT)

/* ===================================================================
 * VCSR-01: V=1 read sstatus accesses vsstatus
 *
 * HS-mode writes a known value to vsstatus, then VS-mode reads
 * sstatus. In V=1, sstatus is substituted by vsstatus, so the
 * read should return the vsstatus value.
 * =================================================================== */
TEST_REGISTER(test_vcsr_01);
bool test_vcsr_01(void)
{
    TEST_BEGIN("VCSR-01: V=1 read sstatus accesses vsstatus");

    uintptr_t test_val = VSSTATUS_TEST_VAL;

    /* Write test value to vsstatus (CSR 0x200) from M-mode. */
    CSRW(CSR_VSSTATUS, test_val);

    /* Read back from M-mode to get the actual stored value (WARL). */
    uintptr_t written;
    written = CSRR(CSR_VSSTATUS);

    /* VS-mode reads sstatus — should return vsstatus value. */
    uintptr_t vs_read = run_in_vs_mode(vs_read_sstatus, 0);

    TEST_ASSERT_EQ("VS sstatus read == vsstatus written",
                   vs_read & VSSTATUS_WRITABLE_MASK,
                   written & VSSTATUS_WRITABLE_MASK);

    HYP_TEST_END();
}

/* ===================================================================
 * VCSR-02: V=1 write sstatus actually writes vsstatus
 *
 * VS-mode writes a value to sstatus. After returning to M-mode,
 * read vsstatus to confirm the write landed on vsstatus.
 * =================================================================== */
TEST_REGISTER(test_vcsr_02);
bool test_vcsr_02(void)
{
    TEST_BEGIN("VCSR-02: V=1 write sstatus writes vsstatus");

    uintptr_t test_val = VSSTATUS_TEST_VAL;

    /* Clear vsstatus before the test. */
    CSRW(CSR_VSSTATUS, 0);

    /* VS-mode writes sstatus (= vsstatus in V=1). */
    run_in_vs_mode(vs_write_sstatus, test_val);

    /* Read vsstatus from M-mode and verify. */
    uintptr_t readback;
    readback = CSRR(CSR_VSSTATUS);

    TEST_ASSERT_EQ("vsstatus contains value written by VS sstatus",
                   readback & VSSTATUS_WRITABLE_MASK,
                   test_val & VSSTATUS_WRITABLE_MASK);

    HYP_TEST_END();
}

/* ===================================================================
 * VCSR-03: V=1 HS-level sstatus is preserved
 *
 * HS-mode sets a value in the real sstatus (CSR 0x100), then
 * VS-mode modifies sstatus (= vsstatus). After returning, verify
 * that HS-level sstatus was NOT affected by the VS-mode write.
 * =================================================================== */
TEST_REGISTER(test_vcsr_03);
bool test_vcsr_03(void)
{
    TEST_BEGIN("VCSR-03: V=1 HS-level sstatus preserved");

    uintptr_t orig_sstatus;
    orig_sstatus = CSRR(CSR_SSTATUS);

    /* Set SIE in real HS-level sstatus. */
    uintptr_t hs_val = SSTATUS_SIE_BIT;
    CSRW(CSR_SSTATUS, orig_sstatus | hs_val);

    /* Confirm the write took effect. */
    uintptr_t hs_before;
    hs_before = CSRR(CSR_SSTATUS);

    /* VS-mode clears sstatus (= vsstatus in V=1). */
    run_in_vs_mode(vs_write_sstatus, 0);

    /* Read HS-level sstatus again — should still have SIE. */
    uintptr_t hs_after;
    hs_after = CSRR(CSR_SSTATUS);

    TEST_ASSERT_EQ("HS-level sstatus.SIE preserved after VS write",
                   hs_after & SSTATUS_SIE_BIT, hs_before & SSTATUS_SIE_BIT);

    /* Restore original sstatus. */
    CSRW(CSR_SSTATUS, orig_sstatus);

    HYP_TEST_END();
}

/* ===================================================================
 * VCSR-04: V=1 direct VS CSR address access triggers virtual-inst
 *
 * VS-mode attempts to read vsstatus using its direct CSR address
 * (0x200). Per the spec, this triggers a virtual-instruction
 * exception (cause=22) when V=1.
 * =================================================================== */
TEST_REGISTER(test_vcsr_04);
bool test_vcsr_04(void)
{
    TEST_BEGIN("VCSR-04: VS direct CSR addr triggers virtual-inst");

    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_read_vsstatus_direct, 0));

    TEST_ASSERT_EQ("trap cause == virtual-inst (22)",
                   trap_get_cause(), CAUSE_VIRTUAL_INSTRUCTION);

    HYP_TEST_END();
}

/* ===================================================================
 * VCSR-05: U-mode direct VS CSR address triggers illegal-inst
 *
 * U-mode (V=0) attempts to read vsstatus using its direct CSR
 * address (0x200). Per the spec, U-mode access to VS CSR triggers
 * an illegal-instruction exception (cause=2).
 *
 * Also tests VU-mode (V=1) which triggers virtual-inst (cause=22).
 * =================================================================== */
TEST_REGISTER(test_vcsr_05);
bool test_vcsr_05(void)
{
    TEST_BEGIN("VCSR-05: U-mode direct VS CSR addr triggers illegal-inst");

    /* Part A: V=0 U-mode access → illegal-instruction (cause=2). */
    EXPECT_TRAP(CAUSE_ILLEGAL_INST,
                run_in_priv(PRIV_U, vs_read_vsstatus_direct, 0));

    TEST_ASSERT_EQ("U-mode trap cause == illegal-inst (2)",
                   trap_get_cause(), (uintptr_t)CAUSE_ILLEGAL_INST);

    /* Part B: V=1 VU-mode access → virtual-instruction (cause=22). */
    EXPECT_VIRTUAL_INST(run_in_vu_mode(vs_read_vsstatus_direct, 0));

    TEST_ASSERT_EQ("VU-mode trap cause == virtual-inst (22)",
                   trap_get_cause(), CAUSE_VIRTUAL_INSTRUCTION);

    HYP_TEST_END();
}

/* ===================================================================
 * VCSR-06: M-mode direct VS CSR access
 *
 * M-mode reads and writes VS CSRs by their direct addresses.
 * Per the spec, M-mode and HS-mode can access VS CSRs directly.
 * =================================================================== */
TEST_REGISTER(test_vcsr_06);
bool test_vcsr_06(void)
{
    TEST_BEGIN("VCSR-06: M-mode direct VS CSR access");

    uintptr_t val, test_val;

    /* vsstatus (0x200). */
    test_val = VSSTATUS_TEST_VAL;
    CSRW(CSR_VSSTATUS, test_val);
    val = CSRR(CSR_VSSTATUS);
    TEST_ASSERT_EQ("vsstatus read/write",
                   val & VSSTATUS_WRITABLE_MASK,
                   test_val & VSSTATUS_WRITABLE_MASK);

    /* vsepc (0x241). */
    test_val = 0x1000;
    CSRW(CSR_VSEPC, test_val);
    val = CSRR(CSR_VSEPC);
    TEST_ASSERT_EQ("vsepc read/write", val, test_val);

    /* vsscratch (0x240). */
    test_val = 0xABCD;
    CSRW(CSR_VSSCRATCH, test_val);
    val = CSRR(CSR_VSSCRATCH);
    TEST_ASSERT_EQ("vsscratch read/write", val, test_val);

    /* vscause (0x242). */
    test_val = 12;  /* instruction page fault — legal cause value */
    CSRW(CSR_VSCAUSE, test_val);
    val = CSRR(CSR_VSCAUSE);
    TEST_ASSERT_EQ("vscause read/write", val, test_val);

    /* vstval (0x243). */
    test_val = 0xDEADBEEF;
    CSRW(CSR_VSTVAL, test_val);
    val = CSRR(CSR_VSTVAL);
    TEST_ASSERT_EQ("vstval read/write", val, test_val);

    HYP_TEST_END();
}

/* HS-mode (V=0, S-mode) trampoline: write then read vsstatus (0x200)
 * by its direct CSR address. Per norm:H_vscsrs_acc_m_hs, VS CSRs are
 * accessible from M/HS-mode by their own address. Invoked via
 * run_in_priv(PRIV_S) to execute in true HS-mode (V=0). */
static uintptr_t hs_access_vsstatus(uintptr_t val)
{
    CSRW(CSR_VSSTATUS, val);
    uintptr_t readback;
    readback = CSRR(CSR_VSSTATUS);
    return readback;
}

/* ===================================================================
 * VCSR-07: HS-mode direct VS CSR access
 *
 * Per norm:H_vscsrs_acc_m_hs, VS CSRs are accessible from M-mode and
 * HS-mode by their own CSR addresses. Part A verifies additional VS
 * CSRs from M-mode (superset access). Part B drops to true HS-mode
 * (V=0, S-mode) via run_in_priv(PRIV_S) to verify direct VS CSR
 * access works at the HS privilege level.
 * =================================================================== */
TEST_REGISTER(test_vcsr_07);
bool test_vcsr_07(void)
{
    TEST_BEGIN("VCSR-07: HS-mode direct VS CSR access");

    uintptr_t val, test_val;

    /* Verify mideleg bits 10/6/2 are read-only 1 (spec requirement).
     * mideleg (0x303) is an M-level CSR; this suite runs in S(HS)-mode, so
     * a raw csrr would trap illegal. Read it through the adaptive tsbi_csr_read()
     * wrapper, which routes to the T-SBI CSR proxy when the current privilege
     * cannot access the register directly. The assertion is unchanged. */
    uintptr_t mideleg = tsbi_csr_read(CSR_MIDELEG);
    TEST_ASSERT("mideleg bits 10/6/2 should be read-only 1",
                (mideleg & 0x444) == 0x444);

    /* --- Part A: M-mode direct access to additional VS CSRs --- */

    /* vsie (0x204) — verify M-mode can read and write.
     * Per spec (norm:vsip_vsie_ssi/sti/sei), vsie bits 1/5/9 are
     * read-only zeros when the corresponding hideleg bits 2/6/10
     * are zero. Set hideleg bits first to make vsie writable. */
    uintptr_t saved_hideleg = hideleg_read();
    hideleg_write(saved_hideleg | (1UL << 2) | (1UL << 6) | (1UL << 10));

    test_val = VSIE_WRITABLE_MASK;
    CSRW(CSR_VSIE, test_val);
    val = CSRR(CSR_VSIE);
    TEST_ASSERT_EQ("vsie read/write from M-mode",
                   val & VSIE_WRITABLE_MASK,
                   test_val & VSIE_WRITABLE_MASK);

    hideleg_write(saved_hideleg);

    /* vstvec (0x205). */
    test_val = 0x2000;
    CSRW(CSR_VSTVEC, test_val);
    val = CSRR(CSR_VSTVEC);
    TEST_ASSERT_EQ("vstvec read/write", val, test_val);

    /* vsatp (0x280). */
    test_val = 0x5678;
    CSRW(CSR_VSATP, test_val);
    val = CSRR(CSR_VSATP);
    TEST_ASSERT_EQ("vsatp read/write", val, test_val);

    /* --- Part B: HS-mode (V=0, S-mode) direct VS CSR access ---
     *
     * Drop to true HS-mode via run_in_priv(PRIV_S). In V=0, S-mode
     * is HS-mode, which per norm:H_vscsrs_acc_m_hs can access VS
     * CSRs by their direct addresses. Write a test value to
     * vsstatus (0x200) from HS-mode and read it back. */
    test_val = VSSTATUS_TEST_VAL;
    trap_expect_begin();
    uintptr_t hs_readback = run_in_priv(PRIV_S, hs_access_vsstatus,
                                        test_val);
    bool hs_trapped = trap_was_triggered();
    trap_expect_end();
    TEST_ASSERT("HS-mode vsstatus access (no trap)", !hs_trapped);
    if (!hs_trapped) {
        TEST_ASSERT_EQ("HS-mode vsstatus read/write",
                       hs_readback & VSSTATUS_WRITABLE_MASK,
                       test_val & VSSTATUS_WRITABLE_MASK);
    }

    HYP_TEST_END();
}

/* ===================================================================
 * VCSR-08: V=0 VS CSR does not affect HS-mode behavior
 *
 * In V=0, vsstatus should not influence the actual HS-level
 * sstatus. We write different SIE values to vsstatus and verify
 * that HS-level sstatus is not affected.
 * =================================================================== */
TEST_REGISTER(test_vcsr_08);
bool test_vcsr_08(void)
{
    TEST_BEGIN("VCSR-08: V=0 VS CSR does not affect behavior");

    uintptr_t orig_sstatus;
    orig_sstatus = CSRR(CSR_SSTATUS);

    /* Set HS-level sstatus.SIE = 1. */
    CSRW(CSR_SSTATUS, orig_sstatus | SSTATUS_SIE_BIT);

    /* Write vsstatus.SIE = 0. */
    uintptr_t vsstatus_val;
    vsstatus_val = CSRR(CSR_VSSTATUS);
    vsstatus_val &= ~SSTATUS_SIE_BIT;
    CSRW(CSR_VSSTATUS, vsstatus_val);

    /* Read HS-level sstatus — SIE should still be 1. */
    uintptr_t hs_read;
    hs_read = CSRR(CSR_SSTATUS);

    TEST_ASSERT_EQ("HS sstatus.SIE unaffected by vsstatus.SIE=0",
                   hs_read & SSTATUS_SIE_BIT, SSTATUS_SIE_BIT);

    /* Write vsstatus.SIE = 1. */
    vsstatus_val = CSRR(CSR_VSSTATUS);
    vsstatus_val |= SSTATUS_SIE_BIT;
    CSRW(CSR_VSSTATUS, vsstatus_val);

    /* Read HS-level sstatus — SIE should still be 1 (unchanged). */
    hs_read = CSRR(CSR_SSTATUS);

    TEST_ASSERT_EQ("HS sstatus.SIE unaffected by vsstatus.SIE=1",
                   hs_read & SSTATUS_SIE_BIT, SSTATUS_SIE_BIT);

    /* Restore original sstatus. */
    CSRW(CSR_SSTATUS, orig_sstatus);

    HYP_TEST_END();
}

/* ===================================================================
 * VCSR-09: V=1 read sepc accesses vsepc
 *
 * M-mode writes a value to vsepc, then VS-mode reads sepc.
 * In V=1, sepc is substituted by vsepc. Account for WARL
 * masking (bit 0 may be cleared for alignment).
 * =================================================================== */
TEST_REGISTER(test_vcsr_09);
bool test_vcsr_09(void)
{
    TEST_BEGIN("VCSR-09: V=1 read sepc accesses vsepc");

    uintptr_t test_val = 0xDEAD;

    /* Write to vsepc (CSR 0x241). */
    CSRW(CSR_VSEPC, test_val);

    /* Read back from M-mode to get WARL-adjusted value. */
    uintptr_t expected;
    expected = CSRR(CSR_VSEPC);

    /* VS-mode reads sepc (= vsepc in V=1). */
    uintptr_t vs_read = run_in_vs_mode(vs_read_sepc, 0);

    TEST_ASSERT_EQ("VS sepc read == vsepc value", vs_read, expected);

    /* --- Part B: VS-mode writes sepc -> writes vsepc ---
     * vsepc[0] is always zero (WARL per spec: sepc[0] is always zero),
     * so use an even-aligned value to avoid WARL masking. */
    test_val = 0xBEEE;
    CSRW(CSR_VSEPC, 0);  /* clear vsepc */
    run_in_vs_mode(vs_write_sepc, test_val);
    uintptr_t wval;
    wval = CSRR(CSR_VSEPC);
    TEST_ASSERT_EQ("vsepc contains value written by VS sepc",
                   wval, test_val);

    HYP_TEST_END();
}

/* ===================================================================
 * VCSR-10: V=1 read scause accesses vscause
 * =================================================================== */
TEST_REGISTER(test_vcsr_10);
bool test_vcsr_10(void)
{
    TEST_BEGIN("VCSR-10: V=1 read scause accesses vscause");

    uintptr_t test_val = 0x1234;

    /* Write to vscause (CSR 0x242). */
    CSRW(CSR_VSCAUSE, test_val);

    /* Read back for WARL-adjusted value. */
    uintptr_t expected;
    expected = CSRR(CSR_VSCAUSE);

    /* VS-mode reads scause (= vscause in V=1). */
    uintptr_t vs_read = run_in_vs_mode(vs_read_scause, 0);

    TEST_ASSERT_EQ("VS scause read == vscause value", vs_read, expected);

    /* --- Part B: VS-mode writes scause -> writes vscause --- */
    test_val = 13;  /* load page fault — legal cause value */
    CSRW(CSR_VSCAUSE, 0);  /* clear vscause */
    run_in_vs_mode(vs_write_scause, test_val);
    uintptr_t wval;
    wval = CSRR(CSR_VSCAUSE);
    TEST_ASSERT_EQ("vscause contains value written by VS scause",
                   wval, test_val);

    HYP_TEST_END();
}

/* ===================================================================
 * VCSR-11: V=1 read stval accesses vstval
 * =================================================================== */
TEST_REGISTER(test_vcsr_11);
bool test_vcsr_11(void)
{
    TEST_BEGIN("VCSR-11: V=1 read stval accesses vstval");

    uintptr_t test_val = 0x12345678;

    /* Write to vstval (CSR 0x243). */
    CSRW(CSR_VSTVAL, test_val);

    /* Read back for WARL-adjusted value. */
    uintptr_t expected;
    expected = CSRR(CSR_VSTVAL);

    /* VS-mode reads stval (= vstval in V=1). */
    uintptr_t vs_read = run_in_vs_mode(vs_read_stval, 0);

    TEST_ASSERT_EQ("VS stval read == vstval value", vs_read, expected);

    /* --- Part B: VS-mode writes stval -> writes vstval --- */
    test_val = 0xCAFEBABE;
    CSRW(CSR_VSTVAL, 0);  /* clear vstval */
    run_in_vs_mode(vs_write_stval, test_val);
    uintptr_t wval;
    wval = CSRR(CSR_VSTVAL);
    TEST_ASSERT_EQ("vstval contains value written by VS stval",
                   wval, test_val);

    HYP_TEST_END();
}

/* ===================================================================
 * VCSR-12: V=1 read stvec accesses vstvec
 * =================================================================== */
TEST_REGISTER(test_vcsr_12);
bool test_vcsr_12(void)
{
    TEST_BEGIN("VCSR-12: V=1 read stvec accesses vstvec");

    uintptr_t test_val = 0x2000;

    /* Write to vstvec (CSR 0x205). */
    CSRW(CSR_VSTVEC, test_val);

    /* Read back. */
    uintptr_t expected;
    expected = CSRR(CSR_VSTVEC);

    /* VS-mode reads stvec (= vstvec in V=1). */
    uintptr_t vs_read = run_in_vs_mode(vs_read_stvec, 0);

    TEST_ASSERT_EQ("VS stvec read == vstvec value", vs_read, expected);

    /* --- Part B: VS-mode writes stvec -> writes vstvec --- */
    test_val = 0x3000;
    CSRW(CSR_VSTVEC, 0);  /* clear vstvec */
    run_in_vs_mode(vs_write_stvec, test_val);
    uintptr_t wval;
    wval = CSRR(CSR_VSTVEC);
    TEST_ASSERT_EQ("vstvec contains value written by VS stvec",
                   wval, test_val);

    HYP_TEST_END();
}

/* ===================================================================
 * VCSR-13: V=1 read sscratch accesses vsscratch
 * =================================================================== */
TEST_REGISTER(test_vcsr_13);
bool test_vcsr_13(void)
{
    TEST_BEGIN("VCSR-13: V=1 read sscratch accesses vsscratch");

    uintptr_t test_val = 0xABCD;

    /* Write to vsscratch (CSR 0x240). */
    CSRW(CSR_VSSCRATCH, test_val);

    /* Read back. */
    uintptr_t expected;
    expected = CSRR(CSR_VSSCRATCH);

    /* VS-mode reads sscratch (= vsscratch in V=1). */
    uintptr_t vs_read = run_in_vs_mode(vs_read_sscratch, 0);

    TEST_ASSERT_EQ("VS sscratch read == vsscratch value",
                   vs_read, expected);

    /* --- Part B: VS-mode writes sscratch -> writes vsscratch --- */
    test_val = 0xFEED;
    CSRW(CSR_VSSCRATCH, 0);  /* clear vsscratch */
    run_in_vs_mode(vs_write_sscratch, test_val);
    uintptr_t wval;
    wval = CSRR(CSR_VSSCRATCH);
    TEST_ASSERT_EQ("vsscratch contains value written by VS sscratch",
                   wval, test_val);

    HYP_TEST_END();
}

/* ===================================================================
 * VCSR-14: V=1 sip/sie access vsip/vsie
 *
 * HS-mode configures vsip/vsie, VS-mode reads sip/sie.
 * Also tests the alias chain through hvip/hie when hideleg
 * enables delegation.
 * =================================================================== */
TEST_REGISTER(test_vcsr_14);
bool test_vcsr_14(void)
{
    TEST_BEGIN("VCSR-14: V=1 sip/sie access vsip/vsie");

    /* Enable dual-layer delegation for VSSI:
     * mideleg[2]=1 (M→HS) + hideleg[2]=1 (HS→VS).
     * This is required for the sie↔vsie↔hie alias chain. */
    /* mideleg is M-level; proxy via tsbi_csr_* (suite runs in S(HS)-mode). */
    uintptr_t mideleg = tsbi_csr_read(CSR_MIDELEG);
    mideleg |= (1UL << 2);
    tsbi_csr_write(CSR_MIDELEG, mideleg);
    hideleg_write(1UL << 2);

    /* --- Part A: sie ↔ hie alias (write from VS, verify from M) ---
     *
     * When hideleg[2]=1, VS-mode writing sie.SSIE (bit 1) should
     * be reflected in hie.VSSIE (bit 2 in VS-level numbering). */
    CSRW(CSR_HIE, 0);  /* hie = 0 */

    run_in_vs_mode(vs_write_sie, 1UL << 1);  /* sie.SSIE = 1 */

    uintptr_t hie_val;
    hie_val = CSRR(CSR_HIE);
    TEST_ASSERT("sie.SSIE write -> hie.VSSIE (bit 2)",
                (hie_val & (1UL << 2)) != 0);

    /* Verify vsie also reflects the write (from M-mode). */
    uintptr_t vsie_val;
    vsie_val = CSRR(CSR_VSIE);
    TEST_ASSERT("vsie.VSSIE set after VS sie write",
                (vsie_val & (1UL << 1)) != 0);

    /* --- Part B: vsip ↔ hvip alias (read from M-mode) ---
     *
     * hip.VSSIP is an alias of hvip.VSSIP (both at bit 2).
     * vsip.SSIP (bit 1) should reflect hvip.VSSIP when hideleg[2]=1. */
    hvip_set_vssi(1);

    (void)hvip_read();
    uintptr_t hip_val;
    hip_val = CSRR(CSR_HIP);

    /* hip.VSSIP (bit 2) should reflect hvip.VSSIP. */
    TEST_ASSERT("hip.VSSIP reflects hvip.VSSIP",
                (hip_val & (1UL << 2)) != 0);

    /* vsip.SSIP (bit 1) from M-mode should reflect hvip.VSSIP. */
    uintptr_t vsip_val;
    vsip_val = CSRR(CSR_VSIP);
    TEST_ASSERT("vsip.SSIP reflects hvip.VSSIP (M-mode read)",
                (vsip_val & (1UL << 1)) != 0);

    /* --- Part C: VS-mode reads sip — alias of vsip ---
     *
     * VS-mode reading sip should get vsip content, where
     * sip.SSIP reflects the VSSIP pending state. */
    uintptr_t sip_val = run_in_vs_mode(vs_read_sip, 0);
    TEST_ASSERT("sip.SSIP reflects VSSIP pending (VS-mode read)",
                (sip_val & (1UL << 1)) != 0);

    /* Cleanup. */
    hvip_set_vssi(0);
    CSRW(CSR_HIE, 0);  /* hie = 0 */
    hideleg_write(0);

    HYP_TEST_END();
}

/* ===================================================================
 * VCSR-15: V=1 read satp accesses vsatp
 *
 * M-mode writes a value to vsatp, VS-mode reads satp.
 * =================================================================== */
TEST_REGISTER(test_vcsr_15);
bool test_vcsr_15(void)
{
    TEST_BEGIN("VCSR-15: V=1 read satp accesses vsatp");

    /* Ensure hstatus.VTVM=0 so VS-mode satp access is not trapped
     * (norm:hstatus_vtvm_op: VTVM=1 causes satp access to trap). */
    hstatus_set_vtvm(0);

    uintptr_t test_val = 0x5678;

    /* Write to vsatp (CSR 0x280). */
    CSRW(CSR_VSATP, test_val);

    /* Read back for actual stored value. */
    uintptr_t expected;
    expected = CSRR(CSR_VSATP);

    /* VS-mode reads satp (= vsatp in V=1). */
    uintptr_t vs_read = run_in_vs_mode(vs_read_satp, 0);

    TEST_ASSERT_EQ("VS satp read == vsatp value", vs_read, expected);

    HYP_TEST_END();
}

/* ===================================================================
 * VCSR-16: senvcfg in V=1 (no VS counterpart)
 *
 * Per norm:H_scsrs_nomatch, senvcfg has no matching VS CSR but
 * "continues to have their usual function and accessibility even
 * when V=1, except with VS-mode and VU-mode substituting for
 * HS-mode and U-mode." Therefore VS-mode (which substitutes for
 * HS-mode) can read/write senvcfg directly — it accesses the real
 * HS-level senvcfg, not a VS substitute. Hypervisor software is
 * expected to manually swap senvcfg during context switches.
 *
 * Per norm:menvcfg_fiom_rdonly0_ok, FIOM may be read-only zero
 * when the Smenvcfg extension is not enabled. Similarly, CBIE/CBCFE
 * require Zicbom, CBZE requires Zicboz. The test probes for any
 * writable field before asserting read/write behavior.
 *
 * When the Smstateen extension is implemented, mstateen0.ENVCFG
 * (bit 62) and hstateen0.ENVCFG (bit 62) gate senvcfg access from
 * HS-mode and VS-mode respectively. These bits may reset to 0 on
 * some platforms (e.g. Sail default). The test enables them before
 * testing VS-mode access so that norm:H_scsrs_nomatch behavior is
 * properly exercised.
 * =================================================================== */
/* VCSR-16 M-mode excursion context and helpers.
 *
 * mstateen0 (0x30C, M-level) and hstateen0 (0x60C, HS-level) carry the ENVCFG
 * gate that controls senvcfg access from HS/VS-mode. Enabling them needs M-mode
 * authority, so this runs inside run_in_priv(PRIV_M, ...).
 *
 * Whether Smstateen exists is a COMPILE-TIME platform declaration
 * (SMSTATEEN_AVAILABLE, normalized by capabilities.h from the config's
 * SMSTATEEN_SUPPORTED) -- NOT a runtime probe. This follows the framework rule
 * that capability support is declaration-driven, never probed: a part that
 * declares Smstateen yet traps on mstateen0 is non-conforming and must fail
 * loudly, not be papered over by a trap probe. */
struct vcsr16_stateen_ctx {
    uintptr_t orig_mstateen0;
    uintptr_t orig_hstateen0;
};

static uintptr_t m_setup_stateen(uintptr_t arg)
{
#if SMSTATEEN_AVAILABLE
    struct vcsr16_stateen_ctx *ctx = (struct vcsr16_stateen_ctx *)arg;

    /* Enable ENVCFG (HS-mode senvcfg access) + SE0 (hstateen0 access) in
     * mstateen0, and ENVCFG in hstateen0 (VS-mode senvcfg access). Save the
     * originals so m_restore_stateen() can put them back. */
    ctx->orig_mstateen0 = CSRR(CSR_MSTATEEN0);
    CSRS(CSR_MSTATEEN0, STATEEN0_ENVCFG | STATEEN0_SE0);
    ctx->orig_hstateen0 = CSRR(CSR_HSTATEEN0);
    CSRS(CSR_HSTATEEN0, STATEEN0_ENVCFG);
#else
    (void)arg;   /* Smstateen not declared: no ENVCFG gate to open */
#endif
    return 0;
}

static uintptr_t m_restore_stateen(uintptr_t arg)
{
#if SMSTATEEN_AVAILABLE
    struct vcsr16_stateen_ctx *ctx = (struct vcsr16_stateen_ctx *)arg;

    CSRW(CSR_HSTATEEN0, ctx->orig_hstateen0);
    CSRW(CSR_MSTATEEN0, ctx->orig_mstateen0);
#else
    (void)arg;
#endif
    return 0;
}

TEST_REGISTER(test_vcsr_16);
bool test_vcsr_16(void)
{
    TEST_BEGIN("VCSR-16: senvcfg in V=1 (no VS counterpart)");

    /* Probe + enable the Smstateen ENVCFG gate in an M-mode excursion FIRST,
     * so the HS-mode senvcfg accesses below are not gated (see helper). */
    struct vcsr16_stateen_ctx ctx;
    run_in_priv(PRIV_M, m_setup_stateen, (uintptr_t)&ctx);

    /* Save original senvcfg (reachable from HS-mode now the gate is open). */
    uintptr_t orig_senvcfg;
    orig_senvcfg = CSRR(CSR_SENVCFG);

    /* Probe for a writable field in senvcfg.
     * FIOM (bit 0) may be read-only zero per norm:menvcfg_fiom_rdonly0_ok
     * when Smenvcfg is not in the ISA string. CBIE (bits [5:4]) requires
     * Zicbom, CBCFE (bit 6) requires Zicbom, CBZE (bit 7) requires Zicboz.
     * Try each known field to find one that is writable. */
    struct {
        uintptr_t val;   /* value to write */
        uintptr_t mask;  /* field mask to check */
        const char *name;
    } probe_fields[] = {
        { 0x01, 0x01, "FIOM" },              /* bit 0 */
        { 0x10, 0x30, "CBIE" },              /* bits [5:4], encoding 01=flush */
        { 0x40, 0x40, "CBCFE" },             /* bit 6 */
        { 0x80, 0x80, "CBZE" },              /* bit 7 */
    };

    uintptr_t test_val = 0;
    uintptr_t test_mask = 0;
    bool found_writable = false;

    for (int i = 0; i < 4; i++) {
        /* Clear senvcfg first, then write the probe value. */
        CSRW(CSR_SENVCFG, 0);
        CSRW(CSR_SENVCFG, probe_fields[i].val);
        uintptr_t rd;
        rd = CSRR(CSR_SENVCFG);
        if ((rd & probe_fields[i].mask) ==
            (probe_fields[i].val & probe_fields[i].mask)) {
            test_val = probe_fields[i].val;
            test_mask = probe_fields[i].mask;
            found_writable = true;
            break;
        }
    }

    /* Part A: M-mode can access senvcfg directly.
     * If a writable field was found, verify M-mode read/write.
     * If no writable field (all read-only zero), skip the assertion
     * but continue to Part B (VS-mode access test). */
    if (found_writable) {
        CSRW(CSR_SENVCFG, test_val);
        uintptr_t m_read;
        m_read = CSRR(CSR_SENVCFG);
        TEST_ASSERT_EQ("M-mode senvcfg read/write",
                       m_read & test_mask, test_val & test_mask);
    } else {
        LOG_W("senvcfg has no writable fields (all read-only zero)\n");
    }

    /* Part B: VS-mode reads senvcfg — should succeed (no trap).
     * senvcfg has no VS counterpart, so VS-mode accesses the real
     * HS-level senvcfg directly. Per norm:H_scsrs_nomatch, this CSR
     * retains its usual accessibility when V=1.
     * When Smstateen is implemented, mstateen0/hstateen0 ENVCFG bits
     * have been enabled above to allow this access. */
    trap_expect_begin();
    run_in_vs_mode(vs_read_senvcfg, 0);
    bool senvcfg_readable = !trap_was_triggered();
    trap_expect_end();
    TEST_ASSERT("VS-mode senvcfg read (no trap per norm:H_scsrs_nomatch)",
                senvcfg_readable);

    /* Part C: VS-mode writes senvcfg — only if read succeeded AND
     * a writable field exists. Clear senvcfg from M-mode first, then
     * have VS-mode write the test value, then verify from M-mode that
     * the write landed on the real HS-level senvcfg. */
    if (senvcfg_readable && found_writable) {
        /* Clear senvcfg to zero from M-mode. */
        CSRW(CSR_SENVCFG, 0);

        trap_expect_begin();
        run_in_vs_mode(vs_write_senvcfg, test_val);
        bool senvcfg_writable = !trap_was_triggered();
        trap_expect_end();
        TEST_ASSERT("VS-mode senvcfg write (no trap)", senvcfg_writable);
        if (senvcfg_writable) {
            uintptr_t m_read;
            m_read = CSRR(CSR_SENVCFG);
            TEST_ASSERT_EQ("VS-mode senvcfg write reflected in M-mode read",
                           m_read & test_mask, test_val & test_mask);
        }
    }

    /* Restore original senvcfg. */
    CSRW(CSR_SENVCFG, orig_senvcfg);

    /* Restore mstateen0/hstateen0 in an M-mode excursion. */
    run_in_priv(PRIV_M, m_restore_stateen, (uintptr_t)&ctx);

    HYP_TEST_END();
}

/* ===================================================================
 * VCSR-17: scounteren in V=1 (no VS counterpart)
 *
 * scounteren has no VS-mode counterpart. In V=1, scounteren
 * controls VU-mode counter visibility. This test verifies:
 *   1. VS-mode can read/write scounteren directly
 *   2. scounteren controls VU-mode counter access
 * =================================================================== */
TEST_REGISTER(test_vcsr_17);
bool test_vcsr_17(void)
{
    TEST_BEGIN("VCSR-17: scounteren in V=1 (no VS counterpart)");

    /* Save original values.
     * mcounteren (0x306) is M-level; the suite runs in S(HS)-mode, so use
     * the tsbi_csr_* wrapper (routes through the T-SBI CSR proxy when
     * the current privilege cannot reach the register). scounteren (S-level)
     * and hcounteren (HS-level) are directly reachable from HS-mode. */
    uintptr_t orig_mcounteren = tsbi_csr_read(CSR_MCOUNTEREN);
    uintptr_t orig_scounteren;
    orig_scounteren = CSRR(CSR_SCOUNTEREN);
    uintptr_t orig_hcounteren = hcounteren_read();

    /* Enable cycle counter access at all levels. */
    tsbi_csr_set(CSR_MCOUNTEREN, 1UL << 0);   /* mcounteren.CY = 1 */
    hcounteren_set(1UL << 0);     /* hcounteren.CY = 1 */
    scounteren_set(1UL << 0);     /* scounteren.CY = 1 */

    /* --- Part A: VS-mode reads scounteren directly ---
     * scounteren (0x106) has no VS counterpart. Per norm:H_scsrs_nomatch,
     * it retains its usual accessibility in V=1, with VS-mode substituting
     * for HS-mode. VS-mode can transparently access scounteren, which in
     * V=1 controls VU-mode counter visibility (the guest OS manages its
     * own user-mode counter permissions). */
    uintptr_t vs_read = run_in_vs_mode(vs_read_scounteren, 0);
    TEST_ASSERT("VS reads scounteren.CY=1", (vs_read & 0x1) == 1);

    /* --- Part B: scounteren=1, VU-mode reads cycle (should succeed) --- */
    VS_EXPECT_NO_TRAP(run_in_vu_mode(vs_read_cycle, 0));
    TEST_ASSERT("VU cycle read succeeds with scounteren.CY=1",
                !trap_was_triggered());

    /* --- Part C: scounteren=0, VU-mode reads cycle (should trap) --- */
    scounteren_clear(1UL << 0);   /* scounteren.CY = 0 */

    trap_expect_begin();
    run_in_vu_mode(vs_read_cycle, 0);
    bool trapped = trap_was_triggered();
    trap_expect_end();

    TEST_ASSERT("VU cycle read traps with scounteren.CY=0", trapped);
    if (trapped) {
        /* Counter denied in VU-mode → virtual-instruction (cause=22)
         * since scounteren is shared and VU counter denial in V=1
         * produces virtual-instruction. */
        TEST_ASSERT("trap cause is virtual-inst or illegal-inst",
                    trap_get_cause() == CAUSE_VIRTUAL_INSTRUCTION ||
                    trap_get_cause() == CAUSE_ILLEGAL_INST);
    }

    /* Restore original values. */
    tsbi_csr_write(CSR_MCOUNTEREN, orig_mcounteren);
    CSRW(CSR_SCOUNTEREN, orig_scounteren);
    hcounteren_write(orig_hcounteren);

    HYP_TEST_END();
}

/* ===================================================================
 * VCSR-18: mtval must not be read-only zero (H extension)
 *
 * norm:H_mtval_nrz: when the hypervisor extension is implemented,
 * CSR mtval must not be read-only zero. A read-only-zero mtval is
 * only legal without the H extension (see Sm_CSR MTRAP-10/11); in
 * this suite the H extension is present, so mtval is required to
 * hold written values. No degraded "read-only zero is acceptable"
 * branch is allowed here.
 * =================================================================== */
TEST_REGISTER(test_vcsr_18);
bool test_vcsr_18(void)
{
    TEST_BEGIN("VCSR-18: mtval is not read-only zero (H ext)");

    /* mtval is a trap-state CSR. mcsr_write_readback() performs the write and
     * the read-back inside a single M-mode excursion, so no intervening trap
     * clobbers it -- the only correct way to check writability from S-mode.
     * (tsbi_csr_read(CSR_MTVAL) is refused by the trap-state guard; see tsbi.h.) */
    uintptr_t rb1 = mcsr_write_readback(CSR_MTVAL, 0xDEADBEEFUL);
    TEST_ASSERT_EQ("mtval must be writable (norm:H_mtval_nrz)",
                   rb1, 0xDEADBEEFUL);

    /* Address-valued round-trip: mtval must hold faulting addresses. */
    uintptr_t addr = (uintptr_t)test_vcsr_18;
    uintptr_t rb2 = mcsr_write_readback(CSR_MTVAL, addr);
    TEST_ASSERT_EQ("mtval must hold an address value", rb2, addr);

    HYP_TEST_END();
}
