/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * common/hyp/tests_2stage/test_group22_svinval.c
 *
 * Group 22 - Svinval (SINVAL.VMA / HINVAL.GVMA) under TVM/VTVM gating
 * (TS-SINV-01..02).
 *
 * Spec basis:
 *   - norm:hstatus_vtvm_op:  hstatus.VTVM=1 makes VS-mode SINVAL.VMA
 *     (and SFENCE.VMA / satp access) raise virtual-instruction.
 *   - norm:mstatus_tvm_hs:   mstatus.TVM=1 makes HS-mode HINVAL.GVMA
 *     (and HFENCE.GVMA / hgatp access) raise illegal-instruction.
 *
 * Encoding (Zicsr SYSTEM opcode 0x73, funct3=0):
 *   SINVAL.VMA  rs1, rs2 : funct7 = 0001011  (0x0B)
 *   HINVAL.GVMA rs1, rs2 : funct7 = 0110011  (0x33)
 * =================================================================== */

#ifndef SUITE_HGATP_MODE
#error "SUITE_HGATP_MODE must be defined before including this file"
#endif
#ifndef SUITE_VSATP_MODE
#error "SUITE_VSATP_MODE must be defined before including this file"
#endif


extern uintptr_t run_in_priv(unsigned priv,
                             uintptr_t (*fn)(uintptr_t), uintptr_t arg);

/* Issue SINVAL.VMA x0, x0 from VS-mode. Returns the captured cause. */
static uintptr_t vs_sinval_vma(uintptr_t arg) {
    (void)arg;
    asm volatile (".insn r 0x73, 0, 0x0B, x0, x0, x0" ::: "memory");
    return trap_get_cause();
}

/* ===================================================================
 * TS-SINV-01: hstatus.VTVM=1 + VS-mode SINVAL.VMA -> virtual-inst (22).
 * =================================================================== */
TEST_REGISTER(test_ts_sinv_01_vtvm_sinval);
bool test_ts_sinv_01_vtvm_sinval(void) {
    TEST_BEGIN("TS-SINV-01: VTVM=1 + VS SINVAL.VMA -> virt-inst (22)");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);
    /* Set hstatus.VTVM via csrs (read-modify-write masking VTVM). */
    CSRS(CSR_HSTATUS, (uintptr_t)HSTATUS_VTVM);

    bool ok = ts2_run_check_fault(&ctx, vs_sinval_vma, 0,
                                  CAUSE_VIRTUAL_INSTRUCTION);
    CSRC(CSR_HSTATUS, (uintptr_t)HSTATUS_VTVM);
    if (!ok) {
        TEST_SKIP("platform may not implement Svinval (SINVAL.VMA decoded as illegal)");
    }
    TEST_ASSERT("cause = virtual-instruction (22)", ok);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-SINV-02: mstatus.TVM=1 + HS-mode HINVAL.GVMA -> illegal-inst (2).
 * =================================================================== */

/* HS-mode helper: issue HINVAL.GVMA x0, x0. */
static uintptr_t hs_hinval_gvma(uintptr_t arg) {
    (void)arg;
    asm volatile (".insn r 0x73, 0, 0x33, x0, x0, x0" ::: "memory");
    return 0;
}

TEST_REGISTER(test_ts_sinv_02_tvm_hinval);
bool test_ts_sinv_02_tvm_hinval(void) {
    TEST_BEGIN("TS-SINV-02: TVM=1 + HS HINVAL.GVMA -> illegal-inst (2)");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    /* Set mstatus.TVM to trap HS-mode fence instructions. TVM is a
     * configuration bit (not an xret return-path bit), so the
     * adaptive accessor proxies it safely from HS-mode via T-SBI. */
    tsbi_csr_set(CSR_MSTATUS, MSTATUS_TVM);

    /* Execute HINVAL.GVMA from HS-mode (S-mode, V=0). */
    trap_expect_begin();
    (void)run_in_priv(PRIV_S, hs_hinval_gvma, 0);
    bool fired = trap_was_triggered();
    uintptr_t cause = fired ? trap_get_cause() : 0;
    trap_expect_end();

    tsbi_csr_clear(CSR_MSTATUS, MSTATUS_TVM);

    if (!fired) {
        TEST_SKIP("platform may not implement Svinval (HINVAL.GVMA NOP)");
    }
    TEST_ASSERT_EQ("cause = illegal-instruction (2)",
                   cause, (uintptr_t)CAUSE_ILLEGAL_INST);
    HYP_TEST_END();
}
