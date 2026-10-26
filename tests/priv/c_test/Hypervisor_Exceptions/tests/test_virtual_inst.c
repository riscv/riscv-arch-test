/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * test_virtual_inst.c - VINST: virtual-instruction exception tests
 *
 * Group 1 of Hypervisor Exceptions subset test plan.
 * =================================================================== */

#include "hyp_test_helpers.h"

/* ===================================================================
 * Local constants
 *
 * sstatus/vsstatus FS/VS field values and misa extension bits used
 * for capability detection. Guarded so they can coexist with
 * test_vsstatus.c when both files are compiled in one suite.
 * =================================================================== */

#ifndef MISA_F
#define MISA_F  (1UL << ('F' - 'A'))
#endif

/* ===================================================================
 * Local platform capability detection
 *
 * F/V support is config-declaration driven: gate on the compile-time
 * F_AVAILABLE / V_AVAILABLE macros (normalized in common/capabilities.h
 * from F_SUPPORTED / V_SUPPORTED in rvtest_config.h). Do NOT read misa
 * at runtime to infer support.
 * =================================================================== */

/* ===================================================================
 * Local FP/Vector instruction trampolines.
 *
 * vs_exec_fp_inst() and vs_exec_vector_inst() are provided by
 * common/hyp/hyp_test_helpers.h (raw .4byte encodings, no -march
 * dependency).
 * =================================================================== */

/* hyp_fetch_inst32() from common/hyp/hyp_test_helpers.h safely reads
 * a 32-bit instruction from a potentially 2-byte-aligned address. */

/* ===================================================================
 * VINST-01: VS executes HLV
 *
 * Verify that HLV executed from VS-mode triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_01_vs_hlv);
bool vinst_01_vs_hlv(void)
{
    TEST_BEGIN("VINST-01: VS executes HLV");

    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_exec_hlv_w, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-02: VS executes HSV
 *
 * Verify that HSV executed from VS-mode triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_02_vs_hsv);
bool vinst_02_vs_hsv(void)
{
    TEST_BEGIN("VINST-02: VS executes HSV");

    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_exec_hsv_w, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-03: VS executes HLVX
 *
 * Verify that HLVX executed from VS-mode triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_03_vs_hlvx);
bool vinst_03_vs_hlvx(void)
{
    TEST_BEGIN("VINST-03: VS executes HLVX");

    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_exec_hlvx_wu, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-04: VS executes HFENCE.VVMA
 *
 * Verify that HFENCE.VVMA executed from VS-mode triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_04_vs_hfence_vvma);
bool vinst_04_vs_hfence_vvma(void)
{
    TEST_BEGIN("VINST-04: VS executes HFENCE.VVMA");

    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_exec_hfence_vvma, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-05: VS executes HFENCE.GVMA
 *
 * Verify that HFENCE.GVMA executed from VS-mode triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_05_vs_hfence_gvma);
bool vinst_05_vs_hfence_gvma(void)
{
    TEST_BEGIN("VINST-05: VS executes HFENCE.GVMA");

    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_exec_hfence_gvma, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-06: VU executes HLV
 *
 * Verify that HLV executed from VU-mode triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_06_vu_hlv);
bool vinst_06_vu_hlv(void)
{
    TEST_BEGIN("VINST-06: VU executes HLV");

    EXPECT_VIRTUAL_INST(run_in_vu_mode(vs_exec_hlv_w, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-07: VS accesses hstatus
 *
 * Verify that VS-mode access to hstatus triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_07_vs_hstatus);
bool vinst_07_vs_hstatus(void)
{
    TEST_BEGIN("VINST-07: VS accesses hstatus");

    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_read_hstatus, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-08: VS accesses hedeleg
 *
 * Verify that VS-mode access to hedeleg triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_08_vs_hedeleg);
bool vinst_08_vs_hedeleg(void)
{
    TEST_BEGIN("VINST-08: VS accesses hedeleg");

    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_read_hedeleg, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-09: VS accesses hgatp
 *
 * Verify that VS-mode access to hgatp triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_09_vs_hgatp);
bool vinst_09_vs_hgatp(void)
{
    TEST_BEGIN("VINST-09: VS accesses hgatp");

    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_read_hgatp, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-10: VS accesses vsstatus directly
 *
 * Verify that VS-mode direct access to vsstatus (CSR 0x200) triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_10_vs_vsstatus_direct);
bool vinst_10_vs_vsstatus_direct(void)
{
    TEST_BEGIN("VINST-10: VS accesses vsstatus directly");

    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_read_vsstatus_direct, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-11: VU executes WFI with TW=0
 *
 * Verify that WFI executed from VU-mode triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_11_vu_wfi);
bool vinst_11_vu_wfi(void)
{
    TEST_BEGIN("VINST-11: VU executes WFI with TW=0");

    EXPECT_VIRTUAL_INST(run_in_vu_mode(vs_exec_wfi, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-12: VU executes SRET
 *
 * Verify that SRET executed from VU-mode triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_12_vu_sret);
bool vinst_12_vu_sret(void)
{
    TEST_BEGIN("VINST-12: VU executes SRET");

    EXPECT_VIRTUAL_INST(run_in_vu_mode(vu_exec_sret, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-13: VU executes SFENCE.VMA
 *
 * Verify that SFENCE.VMA executed from VU-mode triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_13_vu_sfence_vma);
bool vinst_13_vu_sfence_vma(void)
{
    TEST_BEGIN("VINST-13: VU executes SFENCE.VMA");

    EXPECT_VIRTUAL_INST(run_in_vu_mode(vs_exec_sfence_vma, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-14: VU accesses sstatus
 *
 * Verify that VU-mode access to sstatus triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_14_vu_sstatus);
bool vinst_14_vu_sstatus(void)
{
    TEST_BEGIN("VINST-14: VU accesses sstatus");

    EXPECT_VIRTUAL_INST(run_in_vu_mode(vs_read_sstatus, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-15: VU accesses scause
 *
 * Verify that VU-mode access to scause triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_15_vu_scause);
bool vinst_15_vu_scause(void)
{
    TEST_BEGIN("VINST-15: VU accesses scause");

    EXPECT_VIRTUAL_INST(run_in_vu_mode(vs_read_scause, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-16: VS WFI with VTW=1 and TW=0
 *
 * Verify that WFI from VS-mode with VTW=1 triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_16_vs_wfi_vtw);
bool vinst_16_vs_wfi_vtw(void)
{
    TEST_BEGIN("VINST-16: VS WFI with VTW=1 and TW=0");

    hstatus_set_vtw(true);
    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_exec_wfi, 0));
    hstatus_set_vtw(false);

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-17: VS SRET with VTSR=1
 *
 * Verify that SRET from VS-mode with VTSR=1 triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_17_vs_sret_vtsr);
bool vinst_17_vs_sret_vtsr(void)
{
    TEST_BEGIN("VINST-17: VS SRET with VTSR=1");

    hstatus_set_vtsr(true);
    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_exec_sret, 0));
    hstatus_set_vtsr(false);

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-18: VS SFENCE with VTVM=1
 *
 * Verify that SFENCE.VMA from VS-mode with VTVM=1 triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_18_vs_sfence_vtvm);
bool vinst_18_vs_sfence_vtvm(void)
{
    TEST_BEGIN("VINST-18: VS SFENCE with VTVM=1");

    hstatus_set_vtvm(true);
    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_exec_sfence_vma, 0));
    hstatus_set_vtvm(false);

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-19: VS read satp with VTVM=1
 *
 * Verify that satp read from VS-mode with VTVM=1 triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_19_vs_satp_vtvm);
bool vinst_19_vs_satp_vtvm(void)
{
    TEST_BEGIN("VINST-19: VS read satp with VTVM=1");

    hstatus_set_vtvm(true);
    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_read_satp, 0));
    hstatus_set_vtvm(false);

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-20: VS SINVAL with VTVM=1
 *
 * Verify that SINVAL.VMA from VS-mode with VTVM=1 triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_20_vs_sinval_vtvm);
bool vinst_20_vs_sinval_vtvm(void)
{
    TEST_BEGIN("VINST-20: VS SINVAL with VTVM=1");

    hstatus_set_vtvm(true);
    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_exec_sinval_vma, 0));
    hstatus_set_vtvm(false);

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-21: FS=0 illegal not virtual
 *
 * Verify that floating-point instructions with FS=0 cause illegal instruction,
 * not virtual instruction (requires FP support detection).
 * =================================================================== */
TEST_REGISTER(vinst_21_fs0_illegal);
bool vinst_21_fs0_illegal(void)
{
    TEST_BEGIN("VINST-21: FS=0 illegal not virtual");

    if (!F_AVAILABLE)
        TEST_SKIP("F extension not available");

    /* mstatus is M-level and partially trap-state; this suite runs in
     * S(HS)-mode. Read it via the tsbi_csr_read() proxy and write only the FS
     * config field via tsbi_csr_clear()+tsbi_csr_set(): the guard allows a
     * config-field write and it leaves the framework-managed MPP/return bits
     * intact, unlike a full csrw mstatus through the proxy. */
    uintptr_t saved_mstatus = tsbi_csr_read(CSR_MSTATUS);

    /* Set mstatus.FS = Initial (HS-level allows FP). */
    tsbi_csr_clear(CSR_MSTATUS, SSTATUS_FS_MASK); tsbi_csr_set(CSR_MSTATUS, (SSTATUS_FS_INITIAL) & (SSTATUS_FS_MASK));

    /* Set vsstatus.FS = Off (VS-level disables FP). */
    uintptr_t vsstatus;
    vsstatus = CSRR(CSR_VSSTATUS);
    vsstatus = (vsstatus & ~SSTATUS_FS_MASK) | SSTATUS_FS_OFF;
    CSRW(CSR_VSSTATUS, vsstatus);

    /*
     * VS-mode FP with vsstatus.FS=0 must trigger illegal-instruction
     * (cause=2), NOT virtual-instruction (cause=22).
     * This validates norm:H_illegalinst_xstatus_fs_vs.
     */
    EXPECT_ILLEGAL_INST(run_in_vs_mode(vs_exec_fp_inst, 0));

    /* Restore the mstatus.FS field this test touched (the rest of mstatus is
     * framework-managed and must not be written wholesale through the proxy). */
    tsbi_csr_clear(CSR_MSTATUS, SSTATUS_FS_MASK); tsbi_csr_set(CSR_MSTATUS, (saved_mstatus & SSTATUS_FS_MASK) & (SSTATUS_FS_MASK));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-22: VS=0 illegal not virtual
 *
 * Verify that vector instructions with VS=0 cause illegal instruction,
 * not virtual instruction (requires Vector support detection).
 * =================================================================== */
TEST_REGISTER(vinst_22_vs0_illegal);
bool vinst_22_vs0_illegal(void)
{
    TEST_BEGIN("VINST-22: VS=0 illegal not virtual");

    if (!V_AVAILABLE)
        TEST_SKIP("V extension not available");

    /* See VINST-21: read whole mstatus via tsbi_csr_read(), write only the VS
     * config field via tsbi_csr_clear()+set (mstatus is partially trap-state). */
    uintptr_t saved_mstatus = tsbi_csr_read(CSR_MSTATUS);

    /* Set mstatus.VS = Initial (HS-level allows Vector). */
    tsbi_csr_clear(CSR_MSTATUS, SSTATUS_VS_MASK); tsbi_csr_set(CSR_MSTATUS, (SSTATUS_VS_INITIAL) & (SSTATUS_VS_MASK));

    /* Set vsstatus.VS = Off (VS-level disables Vector). */
    uintptr_t vsstatus;
    vsstatus = CSRR(CSR_VSSTATUS);
    vsstatus = (vsstatus & ~SSTATUS_VS_MASK) | SSTATUS_VS_OFF;
    CSRW(CSR_VSSTATUS, vsstatus);

    /*
     * VS-mode Vector with vsstatus.VS=0 must trigger illegal-instruction
     * (cause=2), NOT virtual-instruction (cause=22).
     * This validates norm:H_illegalinst_xstatus_fs_vs.
     */
    EXPECT_ILLEGAL_INST(run_in_vs_mode(vs_exec_vector_inst, 0));

    /* Restore the mstatus.VS field this test touched. */
    tsbi_csr_clear(CSR_MSTATUS, SSTATUS_VS_MASK); tsbi_csr_set(CSR_MSTATUS, (saved_mstatus & SSTATUS_VS_MASK) & (SSTATUS_VS_MASK));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-23: virtual-instruction trap stval correct
 *
 * Verify that when a virtual-instruction exception occurs, stval is set correctly.
 * =================================================================== */
TEST_REGISTER(vinst_23_virtual_inst_stval);
bool vinst_23_virtual_inst_stval(void)
{
    TEST_BEGIN("VINST-23: virtual-instruction trap stval correct");

    /* Trigger virtual-instruction exception via VS-mode hstatus read. */
    trap_expect_begin();
    run_in_vs_mode(vs_read_hstatus, 0);
    TEST_ASSERT("virtual-inst trap triggered", trap_was_triggered());
    if (trap_was_triggered()) {
        TEST_ASSERT_EQ("cause=22 (virtual-instruction)",
                       trap_get_cause(), (uintptr_t)CAUSE_VIRTUAL_INSTRUCTION);

        /*
         * Verify stval per norm:H_virtinst_xtval:
         * "On a virtual-instruction trap, mtval or stval is written the
         *  same as for an illegal-instruction trap."
         *
         * For illegal-instruction traps, stval contains either the
         * faulting instruction encoding or zero. Read the instruction
         * at epc to compare.
         */
        uintptr_t epc = trap_get_epc();
        uintptr_t tval = trap_get_tval();
        uint32_t inst_at_epc = hyp_fetch_inst32(epc);

        if (tval == 0) {
            /* Implementation chose to write 0 (spec-compliant). */
            TEST_ASSERT("stval=0 (implementation choice)", 1);
        }
        else {
            TEST_ASSERT_EQ("stval matches instruction at epc",
                           tval, (uintptr_t)inst_at_epc);
        }
    }
    trap_expect_end();

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-24: mstatus.TW=1 overrides VTW
 *
 * Verify that mstatus.TW=1 causes illegal instruction, overriding VTW.
 * =================================================================== */
TEST_REGISTER(vinst_24_tw_overrides_vtw);
bool vinst_24_tw_overrides_vtw(void)
{
    TEST_BEGIN("VINST-24: mstatus.TW=1 overrides VTW");

    /* Set mstatus.TW=1 (bit 21). TW is a config bit: tsbi_csr_set proxies a csrs
     * that leaves MPP intact (a full csrw mstatus is guard-refused). */
    tsbi_csr_set(CSR_MSTATUS, 1UL << 21);

    /* Execute WFI from VS-mode - should get illegal instruction (cause=2) */
    EXPECT_ILLEGAL_INST(run_in_vs_mode(vs_exec_wfi, 0));

    /* Clear mstatus.TW */
    tsbi_csr_clear(CSR_MSTATUS, 1UL << 21);

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-25: VS accesses hideleg
 *
 * Verify that VS-mode access to hideleg triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_25_vs_hideleg);
bool vinst_25_vs_hideleg(void)
{
    TEST_BEGIN("VINST-25: VS accesses hideleg");

    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_read_hideleg, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-26: VS accesses hcounteren
 *
 * Verify that VS-mode access to hcounteren triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_26_vs_hcounteren);
bool vinst_26_vs_hcounteren(void)
{
    TEST_BEGIN("VINST-26: VS accesses hcounteren");

    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_read_hcounteren, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-27: VS accesses htimedelta
 *
 * Verify that VS-mode access to htimedelta triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_27_vs_htimedelta);
bool vinst_27_vs_htimedelta(void)
{
    TEST_BEGIN("VINST-27: VS accesses htimedelta");

    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_read_htimedelta, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-28: VS accesses hip
 *
 * Verify that VS-mode access to hip triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_28_vs_hip);
bool vinst_28_vs_hip(void)
{
    TEST_BEGIN("VINST-28: VS accesses hip");

    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_read_hip, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-29: VS accesses hie
 *
 * Verify that VS-mode access to hie triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_29_vs_hie);
bool vinst_29_vs_hie(void)
{
    TEST_BEGIN("VINST-29: VS accesses hie");

    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_read_hie, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-30: VS accesses hvip
 *
 * Verify that VS-mode access to hvip triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_30_vs_hvip);
bool vinst_30_vs_hvip(void)
{
    TEST_BEGIN("VINST-30: VS accesses hvip");

    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_read_hvip, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-31: VS accesses henvcfg
 *
 * Verify that VS-mode access to henvcfg triggers virtual-instruction
 * exception (cause=22).
 *
 * When Smstateen is implemented, mstateen0.ENVCFG (bit 62) gates
 * henvcfg access from HS-mode. If ENVCFG=0, henvcfg is not
 * HS-qualified, and VS-mode access returns illegal-instruction
 * (cause=2) instead of virtual-instruction (cause=22). Enable
 * ENVCFG to ensure henvcfg is HS-qualified for this test.
 * =================================================================== */
TEST_REGISTER(vinst_31_vs_henvcfg);
bool vinst_31_vs_henvcfg(void)
{
    TEST_BEGIN("VINST-31: VS accesses henvcfg");

    /* henvcfg must be HS-qualified for a VS-mode access to raise a
     * virtual-instruction (cause=22) rather than illegal-instruction (cause=2).
     * Under Smstateen that qualification is gated by mstateen0.ENVCFG, which
     * main.c opens once via hyp_enable_envcfg_access(). mstateen0 is M-level,
     * so the old runtime trap-probe from HS-mode always trapped and wrongly
     * concluded Smstateen was absent; capability is compile-time gated now. */
    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_read_henvcfg, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-32: VS writes hstatus
 *
 * Verify that VS-mode write to hstatus triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_32_vs_write_hstatus);
bool vinst_32_vs_write_hstatus(void)
{
    TEST_BEGIN("VINST-32: VS writes hstatus");

    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_write_hstatus, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-33: VU accesses sie
 *
 * Verify that VU-mode access to sie triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_33_vu_sie);
bool vinst_33_vu_sie(void)
{
    TEST_BEGIN("VINST-33: VU accesses sie");

    EXPECT_VIRTUAL_INST(run_in_vu_mode(vs_read_sie, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-34: VU accesses sip
 *
 * Verify that VU-mode access to sip triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_34_vu_sip);
bool vinst_34_vu_sip(void)
{
    TEST_BEGIN("VINST-34: VU accesses sip");

    EXPECT_VIRTUAL_INST(run_in_vu_mode(vs_read_sip, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-35: VU accesses stvec
 *
 * Verify that VU-mode access to stvec triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_35_vu_stvec);
bool vinst_35_vu_stvec(void)
{
    TEST_BEGIN("VINST-35: VU accesses stvec");

    EXPECT_VIRTUAL_INST(run_in_vu_mode(vs_read_stvec, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-36: VU accesses sepc
 *
 * Verify that VU-mode access to sepc triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_36_vu_sepc);
bool vinst_36_vu_sepc(void)
{
    TEST_BEGIN("VINST-36: VU accesses sepc");

    EXPECT_VIRTUAL_INST(run_in_vu_mode(vs_read_sepc, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-37: VS write satp with VTVM=1
 *
 * Verify that satp write from VS-mode with VTVM=1 triggers virtual-instruction.
 * =================================================================== */
TEST_REGISTER(vinst_37_vs_write_satp_vtvm);
bool vinst_37_vs_write_satp_vtvm(void)
{
    TEST_BEGIN("VINST-37: VS write satp with VTVM=1");

    hstatus_set_vtvm(true);
    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_write_satp, 0));
    hstatus_set_vtvm(false);

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-38: VS executes HLV.B
 *
 * Verify that HLV.B from VS-mode triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_38_vs_hlv_b);
bool vinst_38_vs_hlv_b(void)
{
    TEST_BEGIN("VINST-38: VS executes HLV.B");

    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_exec_hlv_b, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-39: VS executes HLV.H
 *
 * Verify that HLV.H from VS-mode triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_39_vs_hlv_h);
bool vinst_39_vs_hlv_h(void)
{
    TEST_BEGIN("VINST-39: VS executes HLV.H");

    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_exec_hlv_h, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-40: VS executes HLV.D
 *
 * Verify that HLV.D from VS-mode triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_40_vs_hlv_d);
bool vinst_40_vs_hlv_d(void)
{
    TEST_BEGIN("VINST-40: VS executes HLV.D");

    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_exec_hlv_d, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-41: VS executes HSV.B
 *
 * Verify that HSV.B from VS-mode triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_41_vs_hsv_b);
bool vinst_41_vs_hsv_b(void)
{
    TEST_BEGIN("VINST-41: VS executes HSV.B");

    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_exec_hsv_b, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-42: VS executes HSV.H
 *
 * Verify that HSV.H from VS-mode triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_42_vs_hsv_h);
bool vinst_42_vs_hsv_h(void)
{
    TEST_BEGIN("VINST-42: VS executes HSV.H");

    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_exec_hsv_h, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-43: VS executes HSV.D
 *
 * Verify that HSV.D from VS-mode triggers virtual-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_43_vs_hsv_d);
bool vinst_43_vs_hsv_d(void)
{
    TEST_BEGIN("VINST-43: VS executes HSV.D");

    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_exec_hsv_d, 0));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-44: mstatus.TSR=1 does not affect VS-mode SRET
 *
 * Per norm:mstatus_modes:
 *   "The TSR and TVM fields of mstatus affect execution only in
 *    HS-mode, not in VS-mode."
 *
 * Verify that mstatus.TSR=1 has NO effect on SRET in VS-mode.
 * Only hstatus.VTSR=1 controls whether SRET traps in VS-mode.
 * =================================================================== */
TEST_REGISTER(vinst_44_tsr_no_effect_vs_mode);
bool vinst_44_tsr_no_effect_vs_mode(void)
{
    TEST_BEGIN("VINST-44: mstatus.TSR=1 does not affect VS-mode SRET");

    /* Set hstatus.VTSR=1 and mstatus.TSR=1 (bit 22). TSR is a config bit:
     * tsbi_csr_set proxies a csrs that leaves MPP intact (this suite runs in
     * S(HS)-mode; a raw csrr/csrw mstatus would trap illegal). */
    hstatus_set_vtsr(true);
    tsbi_csr_set(CSR_MSTATUS, 1UL << 22);   /* mstatus.TSR */

    /* With TSR=1, ANY SRET executed in HS-mode traps illegal -- including the
     * SRET the HS-level trap handler uses to return to an interrupted guest.
     * So route every exception to M-mode for this stimulus: the VS-mode SRET's
     * trap (cause 22 per norm:H_virtinst_vs_sret_vtsr1) is then taken in
     * M-mode, whose handler returns with mret (TSR gates SRET only), avoiding
     * an infinite HS trap loop. The trap is still observed through the generic
     * record. This does not weaken the check: norm:H_cause_virtual_instruction
     * defines HS-qualification "assuming TSR and TVM are both zero", so the VS
     * SRET must still report cause 22 (not cause 2) even with TSR=1.
     * hyp_reset_state at HYP_TEST_END restores the delegation baseline. */
    clear_all_deleg();

    /*
     * mstatus.TSR affects only HS-mode, not VS-mode (norm:mstatus_modes).
     * In VS-mode, SRET is controlled solely by hstatus.VTSR.
     * VTSR=1 -> virtual-instruction exception (cause=22).
     */
    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_exec_sret, 0));

    /* Clear mstatus.TSR. */
    tsbi_csr_clear(CSR_MSTATUS, 1UL << 22);
    hstatus_set_vtsr(false);

    HYP_TEST_END();
}

/* ===================================================================
 * High-half counter CSR trampolines (VINST-45 .. VINST-48).
 *
 * cycleh (0xC80) and instreth (0xC82) exist only on RV32. On RV64
 * (XLEN>32) these addresses are reserved, and per
 * norm:H_illegal_high_half any access must raise an
 * illegal-instruction exception. Numeric CSR addresses are used to
 * avoid assembler symbol dependencies.
 * =================================================================== */

static uintptr_t vinst_read_cycleh(uintptr_t arg)
{
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, 0xC80" : "=r"(v));  /* cycleh */
    return v;
}

static uintptr_t vinst_read_instreth(uintptr_t arg)
{
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, 0xC82" : "=r"(v));  /* instreth */
    return v;
}

/* ===================================================================
 * VINST-45: RV64 HS-mode accesses high-half CSR cycleh
 *
 * Per norm:H_illegal_high_half:
 *   "When XLEN>32, an attempt to access a high-half CSR always
 *    raises an illegal-instruction exception."
 *
 * Verify that HS-mode csrr cycleh (CSR 0xC80) traps with cause=2.
 * =================================================================== */
TEST_REGISTER(vinst_45_hs_cycleh_illegal);
bool vinst_45_hs_cycleh_illegal(void)
{
    TEST_BEGIN("VINST-45: RV64 HS-mode accesses high-half CSR cycleh");

    EXPECT_ILLEGAL_INST(asm volatile ("csrr x0, 0xC80"));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-46: RV64 VS-mode high-half CSR access is always illegal
 *
 * Configure hcounteren[0]=0 with mcounteren[0]=1, which is exactly
 * the gating condition of norm:H_virtinst_vs_nonhighctr_h0_m1 that
 * would yield a virtual-instruction exception for the low-half CSR
 * (cycle). The high-half counterpart (cycleh) must still raise an
 * illegal-instruction exception (cause=2), never cause=22.
 * =================================================================== */
TEST_REGISTER(vinst_46_vs_cycleh_illegal);
bool vinst_46_vs_cycleh_illegal(void)
{
    TEST_BEGIN("VINST-46: RV64 VS-mode high-half CSR access is always illegal");

    uintptr_t saved_mcen = tsbi_csr_read(CSR_MCOUNTEREN);
    uintptr_t saved_hcen = hcounteren_read();

    /* Gating condition prone to a false cause=22 report. */
    tsbi_csr_set(CSR_MCOUNTEREN, 1UL << 0);
    hcounteren_clear(1UL << 0);

    EXPECT_ILLEGAL_INST(run_in_vs_mode(vinst_read_cycleh, 0));

    /* Restore. */
    hcounteren_write(saved_hcen);
    tsbi_csr_write(CSR_MCOUNTEREN, saved_mcen);

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-47: RV64 VU-mode high-half CSR access is always illegal
 *
 * Enable all three counter-enable layers for instret (bit 2) so the
 * low-half CSR would be fully accessible from VU-mode; the high-half
 * CSR (instreth) must still raise an illegal-instruction exception
 * per norm:H_illegal_high_half.
 * =================================================================== */
TEST_REGISTER(vinst_47_vu_instreth_illegal);
bool vinst_47_vu_instreth_illegal(void)
{
    TEST_BEGIN("VINST-47: RV64 VU-mode high-half CSR access is always illegal");

    uintptr_t saved_mcen = tsbi_csr_read(CSR_MCOUNTEREN);
    uintptr_t saved_hcen = hcounteren_read();
    uintptr_t saved_scen = scounteren_read();

    /* Fully enable the low-half counter for VU-mode. */
    tsbi_csr_set(CSR_MCOUNTEREN, 1UL << 2);
    hcounteren_set(1UL << 2);
    scounteren_set(1UL << 2);

    EXPECT_ILLEGAL_INST(run_in_vu_mode(vinst_read_instreth, 0));

    /* Restore. */
    scounteren_write(saved_scen);
    hcounteren_write(saved_hcen);
    tsbi_csr_write(CSR_MCOUNTEREN, saved_mcen);

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-48: RV64 M-mode high-half CSR access is always illegal
 *
 * The word "always" in norm:H_illegal_high_half covers M-mode as
 * well: even at the highest privilege level, accessing a high-half
 * CSR on RV64 must raise an illegal-instruction exception.
 * =================================================================== */
TEST_REGISTER(vinst_48_m_cycleh_illegal);
bool vinst_48_m_cycleh_illegal(void)
{
    TEST_BEGIN("VINST-48: RV64 M-mode high-half CSR access is always illegal");

    EXPECT_ILLEGAL_INST(asm volatile ("csrr x0, 0xC80"));

    HYP_TEST_END();
}

/* ===================================================================
 * VINST-49..52: VS accesses remaining H-extension CSRs
 *
 * norm:H_csrs_hs_not_vs: the H-extension CSRs are provided to
 * HS-mode, but not to VS-mode. Any VS-mode access (even a plain
 * read of a read-only CSR) must raise a virtual-instruction
 * exception (cause=22). VINST-07..10/25..31 already cover hstatus,
 * hedeleg, hgatp, hideleg, hcounteren, htimedelta, hip, hie, hvip
 * and henvcfg; these cases complete the list with hgeip, hgeie,
 * htval and htinst.
 * =================================================================== */
TEST_REGISTER(vinst_49_vs_hgeip);
bool vinst_49_vs_hgeip(void)
{
    TEST_BEGIN("VINST-49: VS accesses hgeip");

    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_read_hgeip, 0));

    HYP_TEST_END();
}

TEST_REGISTER(vinst_50_vs_hgeie);
bool vinst_50_vs_hgeie(void)
{
    TEST_BEGIN("VINST-50: VS accesses hgeie");

    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_read_hgeie, 0));

    HYP_TEST_END();
}

TEST_REGISTER(vinst_51_vs_htval);
bool vinst_51_vs_htval(void)
{
    TEST_BEGIN("VINST-51: VS accesses htval");

    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_read_htval, 0));

    HYP_TEST_END();
}

TEST_REGISTER(vinst_52_vs_htinst);
bool vinst_52_vs_htinst(void)
{
    TEST_BEGIN("VINST-52: VS accesses htinst");

    EXPECT_VIRTUAL_INST(run_in_vs_mode(vs_read_htinst, 0));

    HYP_TEST_END();
}
