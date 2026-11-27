/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * test_hcross_svinval.c - Hypervisor × Svinval cross tests
 *
 * Implements 15 test cases from DOCS/testplan/Hypervisor_cross_test_plan.md
 * Group 5: Hypervisor × Svinval.
 *
 * Svinval extension provides fine-grained TLB invalidation:
 *   - HINVAL.VVMA: VS-stage TLB invalidation
 *   - HINVAL.GVMA: G-stage TLB invalidation with VMID semantics
 *   - SFENCE.W.INVAL / SFENCE.INVAL.IR: ordering guarantees
 *
 * Test coverage:
 *   HCROSS-SINVAL-01~04: HINVAL functionality
 *   HCROSS-SINVAL-05~06: VMID semantics
 *   HCROSS-SINVAL-07~12: VS/VU-mode virtual-instruction exceptions
 *   HCROSS-SINVAL-13~14: VS-mode SFENCE.W.INVAL/SFENCE.INVAL.IR (VTVM=0)
 *   HCROSS-SINVAL-15: VU-mode SINVAL.VMA -> virtual-instruction
 * =================================================================== */

#include "test_helpers.h"

/* ===================================================================
 * HCROSS-SINVAL-01: HINVAL.VVMA basic functionality
 *
 * HS-mode modifies VS-stage PTE, executes HINVAL.VVMA to flush TLB,
 * VS-mode verifies new PTE takes effect.
 * =================================================================== */
TEST_REGISTER(test_hcross_svinval_01);
bool test_hcross_svinval_01(void) {
    TEST_BEGIN("HCROSS-SINVAL-01: HINVAL.VVMA basic functionality");

    if (!H_AVAILABLE) TEST_SKIP("H extension not available");
    if (!SVINVAL_AVAILABLE) TEST_SKIP("Platform does not implement Svinval");

    two_stage_ctx_t ctx;
    pt_pool_reset();
    gpt_pool_reset();
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    uintptr_t test_va = (uintptr_t)test_data_area;

    /* VS-mode store to verify initial mapping (RW) */
    uintptr_t result1 = two_stage_run_in_vs(&ctx, probe_store, test_va);
    TEST_ASSERT_EQ("initial VS-mode store succeeded", result1, (uintptr_t)0);

    /* HS-mode modifies VS-stage PTE to read-only (clear W bit) */
    vs_pte_modify(&ctx, test_va, PT_LEVEL_4K, PTE_V|PTE_R|PTE_A|PTE_D);

    /* Execute HINVAL.VVMA + SFENCE.W.INVAL + SFENCE.INVAL.IR */
    HINVAL_VVMA(test_va, 0);
    SFENCE_W_INVAL();
    SFENCE_INVAL_IR();

    /* VS-mode store should now trigger store page-fault */
    uintptr_t result2 = two_stage_run_in_vs(&ctx, probe_store, test_va);
    TEST_ASSERT_EQ("VS-mode store triggered page-fault after HINVAL.VVMA",
                   result2, (uintptr_t)CAUSE_VS_STORE_PAGE_FAULT);

    ts2_finish(&ctx);
    HYP_TEST_END();
}

/* ===================================================================
 * HCROSS-SINVAL-02: HINVAL.GVMA basic functionality
 *
 * HS-mode modifies G-stage PTE, executes HINVAL.GVMA to flush TLB,
 * VS-mode verifies new PTE takes effect.
 * =================================================================== */
TEST_REGISTER(test_hcross_svinval_02);
bool test_hcross_svinval_02(void) {
    TEST_BEGIN("HCROSS-SINVAL-02: HINVAL.GVMA basic functionality");

    if (!H_AVAILABLE) TEST_SKIP("H extension not available");
    if (!SVINVAL_AVAILABLE) TEST_SKIP("Platform does not implement Svinval");

    two_stage_ctx_t ctx;
    pt_pool_reset();
    gpt_pool_reset();
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    uintptr_t test_va = (uintptr_t)test_data_area;
    uintptr_t test_gpa = test_va;  /* identity mapping */

    /* VS-mode store to verify initial mapping */
    uintptr_t result1 = two_stage_run_in_vs(&ctx, probe_store, test_va);
    TEST_ASSERT_EQ("initial VS-mode store succeeded", result1, (uintptr_t)0);

    /* HS-mode modifies G-stage PTE to read-only */
    g_pte_modify(&ctx, test_gpa, PT_LEVEL_4K, PTE_V|PTE_R|PTE_U|PTE_A|PTE_D);

    /* Execute HINVAL.GVMA + SFENCE.W.INVAL + SFENCE.INVAL.IR */
    HINVAL_GVMA(test_gpa >> 2, 0);
    SFENCE_W_INVAL();
    SFENCE_INVAL_IR();

    /* VS-mode store should now trigger store guest-page-fault */
    uintptr_t result2 = two_stage_run_in_vs(&ctx, probe_store, test_va);
    TEST_ASSERT_EQ("VS-mode store triggered guest-page-fault after HINVAL.GVMA",
                   result2, (uintptr_t)CAUSE_STORE_GUEST_PAGE_FAULT);

    ts2_finish(&ctx);
    HYP_TEST_END();
}

/* ===================================================================
 * HCROSS-SINVAL-03: HINVAL.VVMA + SFENCE.W.INVAL/SFENCE.INVAL.IR combo
 *
 * Modify multiple VS-stage PTEs, execute multiple HINVAL.VVMA,
 * then SFENCE.W.INVAL + SFENCE.INVAL.IR, verify all take effect.
 * =================================================================== */
TEST_REGISTER(test_hcross_svinval_03);
bool test_hcross_svinval_03(void) {
    TEST_BEGIN("HCROSS-SINVAL-03: HINVAL.VVMA + SFENCE combo");

    if (!H_AVAILABLE) TEST_SKIP("H extension not available");
    if (!SVINVAL_AVAILABLE) TEST_SKIP("Platform does not implement Svinval");

    two_stage_ctx_t ctx;
    pt_pool_reset();
    gpt_pool_reset();
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    uintptr_t va1 = (uintptr_t)test_data_area;
    uintptr_t va2 = (uintptr_t)test_fault_page;

    /* Modify both PTEs to read-only */
    vs_pte_modify(&ctx, va1, PT_LEVEL_4K, PTE_V|PTE_R|PTE_A|PTE_D);
    vs_pte_modify(&ctx, va2, PT_LEVEL_4K, PTE_V|PTE_R|PTE_A|PTE_D);

    /* Execute multiple HINVAL.VVMA */
    HINVAL_VVMA(va1, 0);
    HINVAL_VVMA(va2, 0);
    SFENCE_W_INVAL();
    SFENCE_INVAL_IR();

    /* Verify both PTEs take effect */
    uintptr_t result1 = two_stage_run_in_vs(&ctx, probe_store, va1);
    uintptr_t result2 = two_stage_run_in_vs(&ctx, probe_store, va2);

    TEST_ASSERT_EQ("va1 store page-fault", result1, (uintptr_t)CAUSE_VS_STORE_PAGE_FAULT);
    TEST_ASSERT_EQ("va2 store page-fault", result2, (uintptr_t)CAUSE_VS_STORE_PAGE_FAULT);

    ts2_finish(&ctx);
    HYP_TEST_END();
}

/* ===================================================================
 * HCROSS-SINVAL-04: HINVAL.GVMA + SFENCE.W.INVAL/SFENCE.INVAL.IR combo
 *
 * Modify multiple G-stage PTEs, execute multiple HINVAL.GVMA,
 * then SFENCE.W.INVAL + SFENCE.INVAL.IR, verify all take effect.
 * =================================================================== */
TEST_REGISTER(test_hcross_svinval_04);
bool test_hcross_svinval_04(void) {
    TEST_BEGIN("HCROSS-SINVAL-04: HINVAL.GVMA + SFENCE combo");

    if (!H_AVAILABLE) TEST_SKIP("H extension not available");
    if (!SVINVAL_AVAILABLE) TEST_SKIP("Platform does not implement Svinval");

    two_stage_ctx_t ctx;
    pt_pool_reset();
    gpt_pool_reset();
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    uintptr_t va1 = (uintptr_t)test_data_area;
    uintptr_t va2 = (uintptr_t)test_fault_page;
    uintptr_t gpa1 = va1;
    uintptr_t gpa2 = va2;

    /* Modify both G-stage PTEs to read-only */
    g_pte_modify(&ctx, gpa1, PT_LEVEL_4K, PTE_V|PTE_R|PTE_U|PTE_A|PTE_D);
    g_pte_modify(&ctx, gpa2, PT_LEVEL_4K, PTE_V|PTE_R|PTE_U|PTE_A|PTE_D);

    /* Execute multiple HINVAL.GVMA */
    HINVAL_GVMA(gpa1 >> 2, 0);
    HINVAL_GVMA(gpa2 >> 2, 0);
    SFENCE_W_INVAL();
    SFENCE_INVAL_IR();

    /* Verify both PTEs take effect */
    uintptr_t result1 = two_stage_run_in_vs(&ctx, probe_store, va1);
    uintptr_t result2 = two_stage_run_in_vs(&ctx, probe_store, va2);

    TEST_ASSERT_EQ("va1 store guest-page-fault", result1, (uintptr_t)CAUSE_STORE_GUEST_PAGE_FAULT);
    TEST_ASSERT_EQ("va2 store guest-page-fault", result2, (uintptr_t)CAUSE_STORE_GUEST_PAGE_FAULT);

    ts2_finish(&ctx);
    HYP_TEST_END();
}

/* ===================================================================
 * HCROSS-SINVAL-05: HINVAL.GVMA with specific VMID
 *
 * Modify G-stage PTE, execute HINVAL.GVMA(gpa, vmid=5),
 * verify VMID=5 TLB is flushed, VMID=6 may still use old TLB.
 * =================================================================== */
TEST_REGISTER(test_hcross_svinval_05);
bool test_hcross_svinval_05(void) {
    TEST_BEGIN("HCROSS-SINVAL-05: HINVAL.GVMA with VMID=5");

    if (!H_AVAILABLE) TEST_SKIP("H extension not available");
    if (!SVINVAL_AVAILABLE) TEST_SKIP("Platform does not implement Svinval");

    two_stage_ctx_t ctx;
    pt_pool_reset();
    gpt_pool_reset();
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    uintptr_t test_va = (uintptr_t)test_data_area;
    uintptr_t test_gpa = test_va;

    /* Modify G-stage PTE to read-only */
    g_pte_modify(&ctx, test_gpa, PT_LEVEL_4K, PTE_V|PTE_R|PTE_U|PTE_A|PTE_D);

    /* Execute HINVAL.GVMA with VMID=5 */
    HINVAL_GVMA(test_gpa >> 2, 5);
    SFENCE_W_INVAL();
    SFENCE_INVAL_IR();

    /* Enable two-stage with VMID=5, verify new PTE takes effect */
    two_stage_enable(&ctx, 5);
    uintptr_t result_vmid5 = two_stage_run_in_vs(&ctx, probe_store, test_va);
    TEST_ASSERT_EQ("VMID=5 store guest-page-fault (new PTE)",
                   result_vmid5, (uintptr_t)CAUSE_STORE_GUEST_PAGE_FAULT);

    /* Note: VMID=6 behavior is implementation-dependent, not tested */

    ts2_finish(&ctx);
    HYP_TEST_END();
}

/* ===================================================================
 * HCROSS-SINVAL-06: HINVAL.GVMA with VMID=0 (flush all VMIDs)
 *
 * Modify G-stage PTE, execute HINVAL.GVMA(gpa, vmid=0),
 * verify all VMIDs' TLBs are flushed.
 * =================================================================== */
TEST_REGISTER(test_hcross_svinval_06);
bool test_hcross_svinval_06(void) {
    TEST_BEGIN("HCROSS-SINVAL-06: HINVAL.GVMA with VMID=0");

    if (!H_AVAILABLE) TEST_SKIP("H extension not available");
    if (!SVINVAL_AVAILABLE) TEST_SKIP("Platform does not implement Svinval");

    two_stage_ctx_t ctx;
    pt_pool_reset();
    gpt_pool_reset();
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    uintptr_t test_va = (uintptr_t)test_data_area;
    uintptr_t test_gpa = test_va;

    /* Modify G-stage PTE to read-only */
    g_pte_modify(&ctx, test_gpa, PT_LEVEL_4K, PTE_V|PTE_R|PTE_U|PTE_A|PTE_D);

    /* Execute HINVAL.GVMA with VMID=0 (flush all) */
    HINVAL_GVMA(test_gpa >> 2, 0);
    SFENCE_W_INVAL();
    SFENCE_INVAL_IR();

    /* Verify VMID=5 uses new PTE */
    two_stage_enable(&ctx, 5);
    uintptr_t result_vmid5 = two_stage_run_in_vs(&ctx, probe_store, test_va);
    TEST_ASSERT_EQ("VMID=5 store guest-page-fault",
                   result_vmid5, (uintptr_t)CAUSE_STORE_GUEST_PAGE_FAULT);

    /* Verify VMID=6 uses new PTE */
    two_stage_enable(&ctx, 6);
    uintptr_t result_vmid6 = two_stage_run_in_vs(&ctx, probe_store, test_va);
    TEST_ASSERT_EQ("VMID=6 store guest-page-fault",
                   result_vmid6, (uintptr_t)CAUSE_STORE_GUEST_PAGE_FAULT);

    ts2_finish(&ctx);
    HYP_TEST_END();
}

/* ===================================================================
 * HCROSS-SINVAL-07: VS-mode HINVAL.VVMA -> virtual-instruction
 *
 * VS-mode executes HINVAL.VVMA, should trigger virtual-instruction
 * exception (cause=22).
 * =================================================================== */
TEST_REGISTER(test_hcross_svinval_07);
bool test_hcross_svinval_07(void) {
    TEST_BEGIN("HCROSS-SINVAL-07: VS-mode HINVAL.VVMA -> virtual-inst");

    if (!H_AVAILABLE) TEST_SKIP("H extension not available");
    if (!SVINVAL_AVAILABLE) TEST_SKIP("Platform does not implement Svinval");

    two_stage_ctx_t ctx;
    pt_pool_reset();
    gpt_pool_reset();
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    trap_expect_begin();
    two_stage_run_in_vs(&ctx, vs_exec_hinval_vvma, 0);
    TEST_ASSERT("virtual-inst trap triggered", trap_was_triggered());
    if (trap_was_triggered()) {
        TEST_ASSERT_EQ("cause=22 (virtual-instruction)",
                       trap_get_cause(), (uintptr_t)CAUSE_VIRTUAL_INSTRUCTION);
    }
    trap_expect_end();

    ts2_finish(&ctx);
    HYP_TEST_END();
}

/* ===================================================================
 * HCROSS-SINVAL-08: VS-mode HINVAL.GVMA -> virtual-instruction
 *
 * VS-mode executes HINVAL.GVMA, should trigger virtual-instruction
 * exception (cause=22).
 * =================================================================== */
TEST_REGISTER(test_hcross_svinval_08);
bool test_hcross_svinval_08(void) {
    TEST_BEGIN("HCROSS-SINVAL-08: VS-mode HINVAL.GVMA -> virtual-inst");

    if (!H_AVAILABLE) TEST_SKIP("H extension not available");
    if (!SVINVAL_AVAILABLE) TEST_SKIP("Platform does not implement Svinval");

    two_stage_ctx_t ctx;
    pt_pool_reset();
    gpt_pool_reset();
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    trap_expect_begin();
    two_stage_run_in_vs(&ctx, vs_exec_hinval_gvma, 0);
    TEST_ASSERT("virtual-inst trap triggered", trap_was_triggered());
    if (trap_was_triggered()) {
        TEST_ASSERT_EQ("cause=22 (virtual-instruction)",
                       trap_get_cause(), (uintptr_t)CAUSE_VIRTUAL_INSTRUCTION);
    }
    trap_expect_end();

    ts2_finish(&ctx);
    HYP_TEST_END();
}

/* ===================================================================
 * HCROSS-SINVAL-09: VU-mode HINVAL.VVMA -> virtual-instruction
 *
 * VU-mode executes HINVAL.VVMA, should trigger virtual-instruction
 * exception (cause=22).
 * =================================================================== */
TEST_REGISTER(test_hcross_svinval_09);
bool test_hcross_svinval_09(void) {
    TEST_BEGIN("HCROSS-SINVAL-09: VU-mode HINVAL.VVMA -> virtual-inst");

    if (!H_AVAILABLE) TEST_SKIP("H extension not available");
    if (!SVINVAL_AVAILABLE) TEST_SKIP("Platform does not implement Svinval");

    two_stage_ctx_t ctx;
    pt_pool_reset();
    gpt_pool_reset();
    ts2_setup_full_u(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    trap_expect_begin();
    two_stage_run_in_vu(&ctx, vu_exec_hinval_vvma, 0);
    TEST_ASSERT("virtual-inst trap triggered", trap_was_triggered());
    if (trap_was_triggered()) {
        TEST_ASSERT_EQ("cause=22 (virtual-instruction)",
                       trap_get_cause(), (uintptr_t)CAUSE_VIRTUAL_INSTRUCTION);
    }
    trap_expect_end();

    ts2_finish(&ctx);
    HYP_TEST_END();
}

/* ===================================================================
 * HCROSS-SINVAL-10: VU-mode HINVAL.GVMA -> virtual-instruction
 *
 * VU-mode executes HINVAL.GVMA, should trigger virtual-instruction
 * exception (cause=22).
 * =================================================================== */
TEST_REGISTER(test_hcross_svinval_10);
bool test_hcross_svinval_10(void) {
    TEST_BEGIN("HCROSS-SINVAL-10: VU-mode HINVAL.GVMA -> virtual-inst");

    if (!H_AVAILABLE) TEST_SKIP("H extension not available");
    if (!SVINVAL_AVAILABLE) TEST_SKIP("Platform does not implement Svinval");

    two_stage_ctx_t ctx;
    pt_pool_reset();
    gpt_pool_reset();
    ts2_setup_full_u(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    trap_expect_begin();
    two_stage_run_in_vu(&ctx, vu_exec_hinval_gvma, 0);
    TEST_ASSERT("virtual-inst trap triggered", trap_was_triggered());
    if (trap_was_triggered()) {
        TEST_ASSERT_EQ("cause=22 (virtual-instruction)",
                       trap_get_cause(), (uintptr_t)CAUSE_VIRTUAL_INSTRUCTION);
    }
    trap_expect_end();

    ts2_finish(&ctx);
    HYP_TEST_END();
}

/* ===================================================================
 * HCROSS-SINVAL-11: VU-mode SFENCE.W.INVAL -> virtual-instruction
 *
 * VU-mode executes SFENCE.W.INVAL, should trigger virtual-instruction
 * exception (cause=22).
 * =================================================================== */
TEST_REGISTER(test_hcross_svinval_11);
bool test_hcross_svinval_11(void) {
    TEST_BEGIN("HCROSS-SINVAL-11: VU-mode SFENCE.W.INVAL -> virtual-inst");

    if (!H_AVAILABLE) TEST_SKIP("H extension not available");
    if (!SVINVAL_AVAILABLE) TEST_SKIP("Platform does not implement Svinval");

    two_stage_ctx_t ctx;
    pt_pool_reset();
    gpt_pool_reset();
    ts2_setup_full_u(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    trap_expect_begin();
    two_stage_run_in_vu(&ctx, vu_exec_sfence_w_inval, 0);
    TEST_ASSERT("virtual-inst trap triggered", trap_was_triggered());
    if (trap_was_triggered()) {
        TEST_ASSERT_EQ("cause=22 (virtual-instruction)",
                       trap_get_cause(), (uintptr_t)CAUSE_VIRTUAL_INSTRUCTION);
    }
    trap_expect_end();

    ts2_finish(&ctx);
    HYP_TEST_END();
}

/* ===================================================================
 * HCROSS-SINVAL-12: VU-mode SFENCE.INVAL.IR -> virtual-instruction
 *
 * VU-mode executes SFENCE.INVAL.IR, should trigger virtual-instruction
 * exception (cause=22).
 * =================================================================== */
TEST_REGISTER(test_hcross_svinval_12);
bool test_hcross_svinval_12(void) {
    TEST_BEGIN("HCROSS-SINVAL-12: VU-mode SFENCE.INVAL.IR -> virtual-inst");

    if (!H_AVAILABLE) TEST_SKIP("H extension not available");
    if (!SVINVAL_AVAILABLE) TEST_SKIP("Platform does not implement Svinval");

    two_stage_ctx_t ctx;
    pt_pool_reset();
    gpt_pool_reset();
    ts2_setup_full_u(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    trap_expect_begin();
    two_stage_run_in_vu(&ctx, vu_exec_sfence_inval_ir, 0);
    TEST_ASSERT("virtual-inst trap triggered", trap_was_triggered());
    if (trap_was_triggered()) {
        TEST_ASSERT_EQ("cause=22 (virtual-instruction)",
                       trap_get_cause(), (uintptr_t)CAUSE_VIRTUAL_INSTRUCTION);
    }
    trap_expect_end();

    ts2_finish(&ctx);
    HYP_TEST_END();
}

/* ===================================================================
 * HCROSS-SINVAL-13: VS-mode SFENCE.W.INVAL (VTVM=0) -> no trap
 *
 * With hstatus.VTVM=0, VS-mode executes SFENCE.W.INVAL,
 * should complete without exception.
 * =================================================================== */
TEST_REGISTER(test_hcross_svinval_13);
bool test_hcross_svinval_13(void) {
    TEST_BEGIN("HCROSS-SINVAL-13: VS-mode SFENCE.W.INVAL (VTVM=0)");

    if (!H_AVAILABLE) TEST_SKIP("H extension not available");
    if (!SVINVAL_AVAILABLE) TEST_SKIP("Platform does not implement Svinval");

    two_stage_ctx_t ctx;
    pt_pool_reset();
    gpt_pool_reset();
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    /* Ensure hstatus.VTVM=0 */
    uintptr_t hstatus = hstatus_read();
    hstatus &= ~HSTATUS_VTVM;
    hstatus_write(hstatus);

    trap_expect_begin();
    two_stage_run_in_vs(&ctx, vs_exec_sfence_w_inval, 0);
    TEST_ASSERT("no trap for SFENCE.W.INVAL in VS-mode", !trap_was_triggered());
    trap_expect_end();

    ts2_finish(&ctx);
    HYP_TEST_END();
}

/* ===================================================================
 * HCROSS-SINVAL-14: VS-mode SFENCE.INVAL.IR (VTVM=0) -> no trap
 *
 * With hstatus.VTVM=0, VS-mode executes SFENCE.INVAL.IR,
 * should complete without exception.
 * =================================================================== */
TEST_REGISTER(test_hcross_svinval_14);
bool test_hcross_svinval_14(void) {
    TEST_BEGIN("HCROSS-SINVAL-14: VS-mode SFENCE.INVAL.IR (VTVM=0)");

    if (!H_AVAILABLE) TEST_SKIP("H extension not available");
    if (!SVINVAL_AVAILABLE) TEST_SKIP("Platform does not implement Svinval");

    two_stage_ctx_t ctx;
    pt_pool_reset();
    gpt_pool_reset();
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    /* Ensure hstatus.VTVM=0 */
    uintptr_t hstatus = hstatus_read();
    hstatus &= ~HSTATUS_VTVM;
    hstatus_write(hstatus);

    trap_expect_begin();
    two_stage_run_in_vs(&ctx, vs_exec_sfence_inval_ir, 0);
    TEST_ASSERT("no trap for SFENCE.INVAL.IR in VS-mode", !trap_was_triggered());
    trap_expect_end();

    ts2_finish(&ctx);
    HYP_TEST_END();
}

/* ===================================================================
 * HCROSS-SINVAL-15: VU-mode SINVAL.VMA -> virtual-instruction
 *
 * VU-mode executes SINVAL.VMA, should trigger virtual-instruction
 * exception (cause=22). Per norm:Svinval_virtual_instruction_vu_vs,
 * "to execute SINVAL.VMA in VU-mode raises a virtual-instruction
 * exception."
 * =================================================================== */
TEST_REGISTER(test_hcross_svinval_15);
bool test_hcross_svinval_15(void) {
    TEST_BEGIN("HCROSS-SINVAL-15: VU-mode SINVAL.VMA -> virtual-inst");

    if (!H_AVAILABLE) TEST_SKIP("H extension not available");
    if (!SVINVAL_AVAILABLE) TEST_SKIP("Platform does not implement Svinval");

    two_stage_ctx_t ctx;
    pt_pool_reset();
    gpt_pool_reset();
    ts2_setup_full_u(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    trap_expect_begin();
    two_stage_run_in_vu(&ctx, vu_exec_sinval_vma, 0);
    TEST_ASSERT("virtual-inst trap triggered", trap_was_triggered());
    if (trap_was_triggered()) {
        TEST_ASSERT_EQ("cause=22 (virtual-instruction)",
                       trap_get_cause(), (uintptr_t)CAUSE_VIRTUAL_INSTRUCTION);
    }
    trap_expect_end();

    ts2_finish(&ctx);
    HYP_TEST_END();
}
