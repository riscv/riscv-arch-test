/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * Test Group 5:  vsstatus csr
 *
 * Tests VSST-01 through VSST-12 verify vsstatus register behavior.
 */

#include "hyp_test_helpers.h"

/* ===================================================================
 * Local constants
 * =================================================================== */

/* F/V extension availability is a compile-time platform capability, taken
 * from F_AVAILABLE / V_AVAILABLE (common/capabilities.h, force-included and
 * derived from config/<platform>/rvtest_config.h). No runtime misa probing. */

/* mstatus field writes use tsbi_csr_clear(CSR_MSTATUS, mask) + tsbi_csr_set()
 * of the config field: mstatus is partially trap-state, so a full proxied write
 * is guard-refused; clear+set of a config field (FS/VS) is the safe form. */

/* ===================================================================
 * VS-mode trampolines: FP and vector instructions
 *
 * vs_exec_fp_inst() and vs_exec_vector_inst() are provided by
 * common/hyp/hyp_test_helpers.h (raw .4byte encodings, no -march
 * dependency).
 * =================================================================== */

/* ===================================================================
 * VSST-01: vsstatus basic read/write
 *
 * Verify vsstatus can be written and read back from M-mode.
 * =================================================================== */
TEST_REGISTER(vsst_01_basic_rw);
bool vsst_01_basic_rw(void)
{
    TEST_BEGIN("VSST-01: vsstatus basic read/write");

    uintptr_t test_val = VSSTATUS_WRITABLE_MASK;

    /* Write vsstatus (CSR 0x200). */
    CSRW(CSR_VSSTATUS, test_val);

    /* Read back and verify writable fields. */
    uintptr_t readback;
    readback = CSRR(CSR_VSSTATUS);

    uintptr_t hw_writable = readback & VSSTATUS_WRITABLE_MASK;

    /* Write zero and verify all hardware-writable bits clear. */
    CSRW(CSR_VSSTATUS, 0);
    readback = CSRR(CSR_VSSTATUS);

    TEST_ASSERT_EQ("vsstatus cleared to zero",
                   readback & hw_writable, 0UL);

    /* Re-write and verify consistent readback (WARL stability). */
    CSRW(CSR_VSSTATUS, test_val);
    readback = CSRR(CSR_VSSTATUS);

    TEST_ASSERT_EQ("vsstatus writable fields consistent readback",
                   readback & VSSTATUS_WRITABLE_MASK, hw_writable);

    HYP_TEST_END();
}

/* ===================================================================
 * VSST-02: V=1 sstatus accesses vsstatus (substitution)
 *
 * Cross-reference: VCSR-01/02. Verify that VS-mode sstatus access
 * actually reads/writes vsstatus.
 * =================================================================== */
TEST_REGISTER(vsst_02_substitution);
bool vsst_02_substitution(void)
{
    TEST_BEGIN("VSST-02: V=1 sstatus accesses vsstatus");

    /* Write a known value to vsstatus from M-mode. */
    uintptr_t test_val = (1UL << 5) | (1UL << 19);  /* SPIE | MXR */
    CSRW(CSR_VSSTATUS, test_val);

    uintptr_t written;
    written = CSRR(CSR_VSSTATUS);

    /* VS-mode reads sstatus — should return vsstatus value. */
    uintptr_t vs_read = run_in_vs_mode(vs_read_sstatus, 0);

    TEST_ASSERT_EQ("VS sstatus read matches vsstatus",
                   vs_read & VSSTATUS_WRITABLE_MASK,
                   written & VSSTATUS_WRITABLE_MASK);

    /* VS-mode writes sstatus, verify vsstatus is modified. */
    CSRW(CSR_VSSTATUS, 0);
    uintptr_t write_val = (1UL << 18);  /* SUM */
    run_in_vs_mode(vs_write_sstatus, write_val);

    uintptr_t readback;
    readback = CSRR(CSR_VSSTATUS);

    TEST_ASSERT_EQ("VS sstatus write lands on vsstatus",
                   readback & (1UL << 18), write_val & (1UL << 18));

    HYP_TEST_END();
}

/* ===================================================================
 * VSST-03: vsstatus.FS=0 causes FP illegal-instruction
 *
 * V=1, vsstatus.FS=Off, mstatus.FS=Initial (HS-level non-zero).
 * FP instruction in VS-mode triggers illegal-instruction (cause=2).
 * =================================================================== */
TEST_REGISTER(vsst_03_fs_off_fp_illegal);
bool vsst_03_fs_off_fp_illegal(void)
{
    TEST_BEGIN("VSST-03: vsstatus.FS=0 FP triggers illegal-inst");

    if (!F_AVAILABLE)
        TEST_SKIP("F extension not available");

    uintptr_t saved_mstatus = tsbi_csr_read(CSR_MSTATUS);

    /* Set mstatus.FS = Initial (HS-level allows FP). */
    tsbi_csr_clear(CSR_MSTATUS, SSTATUS_FS_MASK); tsbi_csr_set(CSR_MSTATUS, (SSTATUS_FS_INITIAL) & (SSTATUS_FS_MASK));

    /* Set vsstatus.FS = Off (VS-level disables FP). */
    uintptr_t vsstatus;
    vsstatus = CSRR(CSR_VSSTATUS);
    vsstatus = (vsstatus & ~SSTATUS_FS_MASK) | SSTATUS_FS_OFF;
    CSRW(CSR_VSSTATUS, vsstatus);

    /* VS-mode FP should trigger illegal-instruction (cause=2). */
    EXPECT_ILLEGAL_INST(run_in_vs_mode(vs_exec_fp_inst, 0));

    /* Restore the mstatus FS/VS fields this test touched (only those were
     * modified; the rest of mstatus is framework-managed). */
    tsbi_csr_clear(CSR_MSTATUS, SSTATUS_FS_MASK); tsbi_csr_set(CSR_MSTATUS, (saved_mstatus & SSTATUS_FS_MASK) & (SSTATUS_FS_MASK));
    tsbi_csr_clear(CSR_MSTATUS, SSTATUS_VS_MASK); tsbi_csr_set(CSR_MSTATUS, (saved_mstatus & SSTATUS_VS_MASK) & (SSTATUS_VS_MASK));

    HYP_TEST_END();
}

/* ===================================================================
 * VSST-04: sstatus.FS=0 causes FP illegal-instruction
 *
 * V=1, mstatus.FS=Off (HS-level disables FP), vsstatus.FS=Initial.
 * FP instruction in VS-mode triggers illegal-instruction (cause=2).
 * =================================================================== */
TEST_REGISTER(vsst_04_sstatus_fs_off_fp_illegal);
bool vsst_04_sstatus_fs_off_fp_illegal(void)
{
    TEST_BEGIN("VSST-04: sstatus.FS=0 FP triggers illegal-inst");

    if (!F_AVAILABLE)
        TEST_SKIP("F extension not available");

    uintptr_t saved_mstatus = tsbi_csr_read(CSR_MSTATUS);

    /* Set mstatus.FS = Off (HS-level disables FP). */
    tsbi_csr_clear(CSR_MSTATUS, SSTATUS_FS_MASK); tsbi_csr_set(CSR_MSTATUS, (SSTATUS_FS_OFF) & (SSTATUS_FS_MASK));

    /* Set vsstatus.FS = Initial (VS-level allows FP). */
    uintptr_t vsstatus;
    vsstatus = CSRR(CSR_VSSTATUS);
    vsstatus = (vsstatus & ~SSTATUS_FS_MASK) | SSTATUS_FS_INITIAL;
    CSRW(CSR_VSSTATUS, vsstatus);

    /* VS-mode FP should trigger illegal-instruction (cause=2). */
    EXPECT_ILLEGAL_INST(run_in_vs_mode(vs_exec_fp_inst, 0));

    /* Restore the mstatus FS/VS fields this test touched (only those were
     * modified; the rest of mstatus is framework-managed). */
    tsbi_csr_clear(CSR_MSTATUS, SSTATUS_FS_MASK); tsbi_csr_set(CSR_MSTATUS, (saved_mstatus & SSTATUS_FS_MASK) & (SSTATUS_FS_MASK));
    tsbi_csr_clear(CSR_MSTATUS, SSTATUS_VS_MASK); tsbi_csr_set(CSR_MSTATUS, (saved_mstatus & SSTATUS_VS_MASK) & (SSTATUS_VS_MASK));

    HYP_TEST_END();
}

/* ===================================================================
 * VSST-05: both FS non-zero allows FP execution
 *
 * V=1, mstatus.FS=Initial, vsstatus.FS=Initial.
 * FP instruction in VS-mode completes without trap.
 * =================================================================== */
TEST_REGISTER(vsst_05_both_fs_nonzero_fp_ok);
bool vsst_05_both_fs_nonzero_fp_ok(void)
{
    TEST_BEGIN("VSST-05: both FS non-zero, FP executes normally");

    if (!F_AVAILABLE)
        TEST_SKIP("F extension not available");

    uintptr_t saved_mstatus = tsbi_csr_read(CSR_MSTATUS);

    /* Set mstatus.FS = Initial. */
    tsbi_csr_clear(CSR_MSTATUS, SSTATUS_FS_MASK); tsbi_csr_set(CSR_MSTATUS, (SSTATUS_FS_INITIAL) & (SSTATUS_FS_MASK));

    /* Set vsstatus.FS = Initial. */
    uintptr_t vsstatus;
    vsstatus = CSRR(CSR_VSSTATUS);
    vsstatus = (vsstatus & ~SSTATUS_FS_MASK) | SSTATUS_FS_INITIAL;
    CSRW(CSR_VSSTATUS, vsstatus);

    /* VS-mode FP should complete without any trap. */
    VS_EXPECT_NO_TRAP(run_in_vs_mode(vs_exec_fp_inst, 0));

    /* Restore the mstatus FS/VS fields this test touched (only those were
     * modified; the rest of mstatus is framework-managed). */
    tsbi_csr_clear(CSR_MSTATUS, SSTATUS_FS_MASK); tsbi_csr_set(CSR_MSTATUS, (saved_mstatus & SSTATUS_FS_MASK) & (SSTATUS_FS_MASK));
    tsbi_csr_clear(CSR_MSTATUS, SSTATUS_VS_MASK); tsbi_csr_set(CSR_MSTATUS, (saved_mstatus & SSTATUS_VS_MASK) & (SSTATUS_VS_MASK));

    HYP_TEST_END();
}

/* ===================================================================
 * VSST-06: FP write makes both FS fields Dirty
 *
 * V=1, both mstatus.FS and vsstatus.FS set to Initial.
 * After VS-mode FP write, both must transition to Dirty (3).
 * =================================================================== */
TEST_REGISTER(vsst_06_fp_makes_both_fs_dirty);
bool vsst_06_fp_makes_both_fs_dirty(void)
{
    TEST_BEGIN("VSST-06: FP write makes both FS Dirty");

    if (!F_AVAILABLE)
        TEST_SKIP("F extension not available");

    uintptr_t saved_mstatus = tsbi_csr_read(CSR_MSTATUS);

    /* Set mstatus.FS = Initial. */
    tsbi_csr_clear(CSR_MSTATUS, SSTATUS_FS_MASK); tsbi_csr_set(CSR_MSTATUS, (SSTATUS_FS_INITIAL) & (SSTATUS_FS_MASK));

    /* Set vsstatus.FS = Initial. */
    uintptr_t vsstatus;
    vsstatus = CSRR(CSR_VSSTATUS);
    vsstatus = (vsstatus & ~SSTATUS_FS_MASK) | SSTATUS_FS_INITIAL;
    CSRW(CSR_VSSTATUS, vsstatus);

    /* Execute FP instruction in VS-mode. */
    run_in_vs_mode(vs_exec_fp_inst, 0);

    /* Check mstatus.FS == Dirty (3). */
    uintptr_t mstatus_after = tsbi_csr_read(CSR_MSTATUS);
    TEST_ASSERT_EQ("mstatus.FS == Dirty",
                   mstatus_after & SSTATUS_FS_MASK, SSTATUS_FS_DIRTY);

    /* Check vsstatus.FS == Dirty (3). */
    uintptr_t vsstatus_after;
    vsstatus_after = CSRR(CSR_VSSTATUS);
    TEST_ASSERT_EQ("vsstatus.FS == Dirty",
                   vsstatus_after & SSTATUS_FS_MASK, SSTATUS_FS_DIRTY);

    /* Restore the mstatus FS/VS fields this test touched (only those were
     * modified; the rest of mstatus is framework-managed). */
    tsbi_csr_clear(CSR_MSTATUS, SSTATUS_FS_MASK); tsbi_csr_set(CSR_MSTATUS, (saved_mstatus & SSTATUS_FS_MASK) & (SSTATUS_FS_MASK));
    tsbi_csr_clear(CSR_MSTATUS, SSTATUS_VS_MASK); tsbi_csr_set(CSR_MSTATUS, (saved_mstatus & SSTATUS_VS_MASK) & (SSTATUS_VS_MASK));

    HYP_TEST_END();
}

/* ===================================================================
 * VSST-07: vsstatus.VS=0 causes Vector illegal-instruction
 *
 * V=1, vsstatus.VS=Off, mstatus.VS=Initial (HS-level non-zero).
 * Vector instruction in VS-mode triggers illegal-instruction (cause=2).
 * =================================================================== */
TEST_REGISTER(vsst_07_vs_off_vector_illegal);
bool vsst_07_vs_off_vector_illegal(void)
{
    TEST_BEGIN("VSST-07: vsstatus.VS=0 Vector triggers illegal-inst");

    if (!V_AVAILABLE)
        TEST_SKIP("V extension not available");

    uintptr_t saved_mstatus = tsbi_csr_read(CSR_MSTATUS);

    /* Set mstatus.VS = Initial (HS-level allows Vector). */
    tsbi_csr_clear(CSR_MSTATUS, SSTATUS_VS_MASK); tsbi_csr_set(CSR_MSTATUS, (SSTATUS_VS_INITIAL) & (SSTATUS_VS_MASK));

    /* Set vsstatus.VS = Off (VS-level disables Vector). */
    uintptr_t vsstatus;
    vsstatus = CSRR(CSR_VSSTATUS);
    vsstatus = (vsstatus & ~SSTATUS_VS_MASK) | SSTATUS_VS_OFF;
    CSRW(CSR_VSSTATUS, vsstatus);

    /* VS-mode Vector should trigger illegal-instruction (cause=2). */
    EXPECT_ILLEGAL_INST(run_in_vs_mode(vs_exec_vector_inst, 0));

    /* Restore the mstatus FS/VS fields this test touched (only those were
     * modified; the rest of mstatus is framework-managed). */
    tsbi_csr_clear(CSR_MSTATUS, SSTATUS_FS_MASK); tsbi_csr_set(CSR_MSTATUS, (saved_mstatus & SSTATUS_FS_MASK) & (SSTATUS_FS_MASK));
    tsbi_csr_clear(CSR_MSTATUS, SSTATUS_VS_MASK); tsbi_csr_set(CSR_MSTATUS, (saved_mstatus & SSTATUS_VS_MASK) & (SSTATUS_VS_MASK));

    HYP_TEST_END();
}

/* ===================================================================
 * VSST-08: sstatus.VS=0 causes Vector illegal-instruction
 *
 * V=1, mstatus.VS=Off (HS-level disables Vector), vsstatus.VS=Initial.
 * Vector instruction in VS-mode triggers illegal-instruction (cause=2).
 * =================================================================== */
TEST_REGISTER(vsst_08_sstatus_vs_off_vector_illegal);
bool vsst_08_sstatus_vs_off_vector_illegal(void)
{
    TEST_BEGIN("VSST-08: sstatus.VS=0 Vector triggers illegal-inst");

    if (!V_AVAILABLE)
        TEST_SKIP("V extension not available");

    uintptr_t saved_mstatus = tsbi_csr_read(CSR_MSTATUS);

    /* Set mstatus.VS = Off (HS-level disables Vector). */
    tsbi_csr_clear(CSR_MSTATUS, SSTATUS_VS_MASK); tsbi_csr_set(CSR_MSTATUS, (SSTATUS_VS_OFF) & (SSTATUS_VS_MASK));

    /* Set vsstatus.VS = Initial (VS-level allows Vector). */
    uintptr_t vsstatus;
    vsstatus = CSRR(CSR_VSSTATUS);
    vsstatus = (vsstatus & ~SSTATUS_VS_MASK) | SSTATUS_VS_INITIAL;
    CSRW(CSR_VSSTATUS, vsstatus);

    /* VS-mode Vector should trigger illegal-instruction (cause=2). */
    EXPECT_ILLEGAL_INST(run_in_vs_mode(vs_exec_vector_inst, 0));

    /* Restore the mstatus FS/VS fields this test touched (only those were
     * modified; the rest of mstatus is framework-managed). */
    tsbi_csr_clear(CSR_MSTATUS, SSTATUS_FS_MASK); tsbi_csr_set(CSR_MSTATUS, (saved_mstatus & SSTATUS_FS_MASK) & (SSTATUS_FS_MASK));
    tsbi_csr_clear(CSR_MSTATUS, SSTATUS_VS_MASK); tsbi_csr_set(CSR_MSTATUS, (saved_mstatus & SSTATUS_VS_MASK) & (SSTATUS_VS_MASK));

    HYP_TEST_END();
}

/* ===================================================================
 * VSST-09: Vector write makes both VS fields Dirty
 *
 * V=1, both mstatus.VS and vsstatus.VS set to Initial.
 * After VS-mode Vector instruction, both must transition to Dirty (3).
 * =================================================================== */
TEST_REGISTER(vsst_09_vector_makes_both_vs_dirty);
bool vsst_09_vector_makes_both_vs_dirty(void)
{
    TEST_BEGIN("VSST-09: Vector write makes both VS Dirty");

    if (!V_AVAILABLE)
        TEST_SKIP("V extension not available");

    uintptr_t saved_mstatus = tsbi_csr_read(CSR_MSTATUS);

    /* Set mstatus.VS = Initial. */
    tsbi_csr_clear(CSR_MSTATUS, SSTATUS_VS_MASK); tsbi_csr_set(CSR_MSTATUS, (SSTATUS_VS_INITIAL) & (SSTATUS_VS_MASK));

    /* Set vsstatus.VS = Initial. */
    uintptr_t vsstatus;
    vsstatus = CSRR(CSR_VSSTATUS);
    vsstatus = (vsstatus & ~SSTATUS_VS_MASK) | SSTATUS_VS_INITIAL;
    CSRW(CSR_VSSTATUS, vsstatus);

    /* Execute Vector instruction in VS-mode. */
    run_in_vs_mode(vs_exec_vector_inst, 0);

    /* Check mstatus.VS == Dirty (3). */
    uintptr_t mstatus_after = tsbi_csr_read(CSR_MSTATUS);
    TEST_ASSERT_EQ("mstatus.VS == Dirty",
                   mstatus_after & SSTATUS_VS_MASK, SSTATUS_VS_DIRTY);

    /* Check vsstatus.VS == Dirty (3). */
    uintptr_t vsstatus_after;
    vsstatus_after = CSRR(CSR_VSSTATUS);
    TEST_ASSERT_EQ("vsstatus.VS == Dirty",
                   vsstatus_after & SSTATUS_VS_MASK, SSTATUS_VS_DIRTY);

    /* Restore the mstatus FS/VS fields this test touched (only those were
     * modified; the rest of mstatus is framework-managed). */
    tsbi_csr_clear(CSR_MSTATUS, SSTATUS_FS_MASK); tsbi_csr_set(CSR_MSTATUS, (saved_mstatus & SSTATUS_FS_MASK) & (SSTATUS_FS_MASK));
    tsbi_csr_clear(CSR_MSTATUS, SSTATUS_VS_MASK); tsbi_csr_set(CSR_MSTATUS, (saved_mstatus & SSTATUS_VS_MASK) & (SSTATUS_VS_MASK));

    HYP_TEST_END();
}

/* ===================================================================
 * VSST-10: vsstatus.SD reflects VS-mode view only
 *
 * SD is computed from FS/VS/XS in vsstatus only (not sstatus).
 * When vsstatus.FS=Clean and vsstatus.VS=Clean, SD should be 0.
 * When vsstatus.FS=Dirty, SD should be 1.
 *
 * Cross-validation (norm:vsstatus_sd_xs_op):
 * HS-level sstatus.FS must NOT affect vsstatus.SD. Setting
 * mstatus.FS=Dirty while vsstatus.FS=Off must leave SD=0.
 * =================================================================== */
TEST_REGISTER(vsst_10_sd_reflects_vs_view);
bool vsst_10_sd_reflects_vs_view(void)
{
    TEST_BEGIN("VSST-10: vsstatus.SD reflects VS-mode view");

    /* Set vsstatus.FS = Clean, vsstatus.VS = Off (no dirty state). */
    uintptr_t vsstatus;
    vsstatus = CSRR(CSR_VSSTATUS);
    vsstatus = (vsstatus & ~(SSTATUS_FS_MASK | SSTATUS_VS_MASK))
               | SSTATUS_FS_CLEAN | SSTATUS_VS_OFF;
    CSRW(CSR_VSSTATUS, vsstatus);

    /* Read back — SD should be 0 (nothing dirty). */
    uintptr_t readback;
    readback = CSRR(CSR_VSSTATUS);
    TEST_ASSERT_EQ("SD=0 when FS=Clean, VS=Off",
                   readback & SSTATUS_SD_BIT, 0UL);

    /* Set vsstatus.FS = Dirty → SD should become 1. */
    vsstatus = (readback & ~SSTATUS_FS_MASK) | SSTATUS_FS_DIRTY;
    CSRW(CSR_VSSTATUS, vsstatus);

    readback = CSRR(CSR_VSSTATUS);
    TEST_ASSERT_EQ("SD=1 when FS=Dirty",
                   readback & SSTATUS_SD_BIT, SSTATUS_SD_BIT);

    /* Set vsstatus.FS = Off, vsstatus.VS = Dirty → SD should be 1. */
    if (V_AVAILABLE) {
        vsstatus = (readback & ~(SSTATUS_FS_MASK | SSTATUS_VS_MASK))
                   | SSTATUS_FS_OFF | SSTATUS_VS_DIRTY;
        CSRW(CSR_VSSTATUS, vsstatus);

        readback = CSRR(CSR_VSSTATUS);
        TEST_ASSERT_EQ("SD=1 when VS=Dirty",
                       readback & SSTATUS_SD_BIT, SSTATUS_SD_BIT);
    }

    /* Cross-validation: mstatus.FS=Dirty + vsstatus.FS=Off → SD=0.
     * HS-level sstatus.FS must NOT influence vsstatus.SD. */
    {
        uintptr_t saved_mstatus = tsbi_csr_read(CSR_MSTATUS);

        /* Set mstatus.FS = Dirty at HS level. */
        tsbi_csr_clear(CSR_MSTATUS, SSTATUS_FS_MASK); tsbi_csr_set(CSR_MSTATUS, (SSTATUS_FS_DIRTY) & (SSTATUS_FS_MASK));

        /* Set vsstatus.FS = Off, vsstatus.VS = Off. */
        vsstatus = (vsstatus & ~(SSTATUS_FS_MASK | SSTATUS_VS_MASK))
                   | SSTATUS_FS_OFF | SSTATUS_VS_OFF;
        CSRW(CSR_VSSTATUS, vsstatus);

        readback = CSRR(CSR_VSSTATUS);
        TEST_ASSERT_EQ("SD=0 despite mstatus.FS=Dirty (HS independent)",
                       readback & SSTATUS_SD_BIT, 0UL);

        /* Also verify HS sstatus.SD IS set (mstatus.FS=Dirty). sstatus is
         * S-level, directly readable from HS-mode. */
        uintptr_t hs_sstatus;
        hs_sstatus = CSRR(CSR_SSTATUS);
        TEST_ASSERT_EQ("HS sstatus.SD=1 when mstatus.FS=Dirty",
                       hs_sstatus & SSTATUS_SD_BIT, SSTATUS_SD_BIT);

        /* Restore the mstatus FS/VS fields this test touched. */
        tsbi_csr_clear(CSR_MSTATUS, SSTATUS_FS_MASK); tsbi_csr_set(CSR_MSTATUS, (saved_mstatus & SSTATUS_FS_MASK) & (SSTATUS_FS_MASK));
        tsbi_csr_clear(CSR_MSTATUS, SSTATUS_VS_MASK); tsbi_csr_set(CSR_MSTATUS, (saved_mstatus & SSTATUS_VS_MASK) & (SSTATUS_VS_MASK));
    }

    HYP_TEST_END();
}

/* ===================================================================
 * VSST-11: V=0 vsstatus does not affect HS-mode behavior
 *
 * Setting vsstatus.SIE=0 in V=0 context should NOT disable
 * HS-mode supervisor interrupts (sstatus.SIE is independent).
 * =================================================================== */
TEST_REGISTER(vsst_11_v0_no_effect);
bool vsst_11_v0_no_effect(void)
{
    TEST_BEGIN("VSST-11: V=0 vsstatus does not affect HS behavior");

    /* Save and set sstatus.SIE = 1 (HS-mode interrupt enable). */
    uintptr_t saved_sstatus;
    saved_sstatus = CSRR(CSR_SSTATUS);
    CSRS(CSR_SSTATUS, SSTATUS_SIE_BIT);

    /* Clear vsstatus.SIE = 0 — must NOT affect HS-mode. */
    uintptr_t vsstatus;
    vsstatus = CSRR(CSR_VSSTATUS);
    vsstatus &= ~SSTATUS_SIE_BIT;
    CSRW(CSR_VSSTATUS, vsstatus);

    /* Verify HS-mode sstatus.SIE is still 1. */
    uintptr_t sstatus;
    sstatus = CSRR(CSR_SSTATUS);
    TEST_ASSERT_EQ("HS sstatus.SIE unaffected by vsstatus.SIE=0",
                   sstatus & SSTATUS_SIE_BIT, SSTATUS_SIE_BIT);

    /* Restore sstatus. */
    CSRW(CSR_SSTATUS, saved_sstatus);

    HYP_TEST_END();
}

/* ===================================================================
 * VSST-12: UXL field read/write (WARL)
 *
 * vsstatus.UXL controls VU-mode XLEN. On RV64, valid values
 * are typically 2 (XLEN=64). The field is WARL; write and read back
 * to verify the implementation accepts or silently constrains the value.
 * =================================================================== */
TEST_REGISTER(vsst_12_uxl_rw);
bool vsst_12_uxl_rw(void)
{
    TEST_BEGIN("VSST-12: UXL field read/write WARL");

    /* Read current vsstatus.UXL. */
    uintptr_t vsstatus;
    vsstatus = CSRR(CSR_VSSTATUS);
    uintptr_t original_uxl = (vsstatus >> SSTATUS_UXL_SHIFT) & 3UL;

    /* UXL should have a valid value (1=32, 2=64, 3=128). */
    TEST_ASSERT("UXL has valid initial value",
                original_uxl >= 1 && original_uxl <= 3);

    /* Try writing UXL = 2 (XLEN=64, the common RV64 value). */
    uintptr_t new_vsstatus = (vsstatus & ~SSTATUS_UXL_MASK)
                             | (2UL << SSTATUS_UXL_SHIFT);
    CSRW(CSR_VSSTATUS, new_vsstatus);

    uintptr_t readback;
    readback = CSRR(CSR_VSSTATUS);
    uintptr_t readback_uxl = (readback >> SSTATUS_UXL_SHIFT) & 3UL;

    /* WARL: implementation may keep original value or accept new one. */
    TEST_ASSERT("UXL WARL: value is valid after write",
                readback_uxl >= 1 && readback_uxl <= 3);

    /* Try writing an unsupported value (e.g., UXL=3 for 128-bit).
     * The field is WARL, so the implementation should either accept
     * it or silently constrain it to a legal value. */
    new_vsstatus = (vsstatus & ~SSTATUS_UXL_MASK)
                   | (3UL << SSTATUS_UXL_SHIFT);
    CSRW(CSR_VSSTATUS, new_vsstatus);

    readback = CSRR(CSR_VSSTATUS);
    readback_uxl = (readback >> SSTATUS_UXL_SHIFT) & 3UL;

    TEST_ASSERT("UXL WARL: legal value after writing 3",
                readback_uxl >= 1 && readback_uxl <= 3);

    /* Restore original UXL. */
    CSRW(CSR_VSSTATUS, vsstatus);

    HYP_TEST_END();
}
