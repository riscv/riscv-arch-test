/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_hcross_svadu.c - Group 1: Hypervisor × Svadu Cross Tests
 *
 * Per DOCS/testplan/Hypervisor_cross_test_plan.md Group 1:
 *   HCROSS-SVADU-01: henvcfg.ADUE writability
 *   HCROSS-SVADU-02: HLV with Svadu (ADUE=1, A-bit HW update)
 *   HCROSS-SVADU-03: HSV with Svadu (ADUE=1, D-bit HW update)
 *   HCROSS-SVADU-04: HLV with Svade (ADUE=0, guest-page-fault)
 *   HCROSS-SVADU-05: menvcfg.ADUE change + HFENCE.GVMA(x0,x0) sync
 *   HCROSS-SVADU-06: menvcfg.ADUE change + HFENCE.GVMA(vmid,x0) sync
 *   HCROSS-SVADU-07: henvcfg.ADUE change + HFENCE.VVMA(x0,x0) sync
 *
 * Normative references:
 *   norm:henvcfg_adue_op         - ADUE controls VS-stage A/D HW update
 *   norm:svadu_henvcfg_adue_writable - henvcfg.ADUE must be writable
 *   norm:svadu_hfence_gvma_sync  - HFENCE.GVMA required after menvcfg.ADUE change
 *   hyp-mm-fences                - HFENCE.VVMA suffices after henvcfg.ADUE change
 */

/* ===================================================================
 * HCROSS-SVADU-01: henvcfg.ADUE writability
 *
 * Verify that henvcfg.ADUE is writable when Svadu is implemented,
 * or read-only zero when Svadu is not implemented.
 * =================================================================== */
TEST_REGISTER(test_hcross_svadu_01);
bool test_hcross_svadu_01(void) {
    TEST_BEGIN("HCROSS-SVADU-01: henvcfg.ADUE writability");

    if (!H_AVAILABLE) TEST_SKIP("H extension not available");

    if (SVADU_AVAILABLE) {
        /* Svadu implemented: menvcfg.ADUE is writable, so henvcfg.ADUE
         * should also be writable (norm:Svadu_hypervisor_adue_writable).
         * Must set menvcfg.ADUE=1 first, otherwise henvcfg.ADUE is
         * read-only zero (norm:menvcfg_adue_henvcfg_adue_rdonly0). */
        uintptr_t old_menvcfg = tsbi_csr_read(CSR_MENVCFG);
        menvcfg_adue_set(1);

        uintptr_t old_henvcfg = henvcfg_read();

        /* Try to write henvcfg.ADUE=1 */
        henvcfg_set_adue(1);
        int readback_1 = henvcfg_adue_read();

        /* Try to write henvcfg.ADUE=0 */
        henvcfg_set_adue(0);
        int readback_0 = henvcfg_adue_read();

        /* Restore original values */
        henvcfg_write(old_henvcfg);
        tsbi_csr_write(CSR_MENVCFG, old_menvcfg);

        TEST_ASSERT("ADUE=1 writable", readback_1 == 1);
        TEST_ASSERT("ADUE=0 writable", readback_0 == 0);
    } else {
        /* Svadu not implemented: henvcfg.ADUE must be read-only zero. */
        henvcfg_set_adue(1);
        int readback_1 = henvcfg_adue_read();
        TEST_ASSERT("ADUE read-only zero without Svadu", readback_1 == 0);
    }

    HYP_TEST_END();
}

/* ===================================================================
 * HCROSS-SVADU-02: HLV with Svadu (ADUE=1, A-bit HW update)
 *
 * Setup: henvcfg.ADUE=1, VS-stage PTE A=0
 * Action: HS-mode executes HLV.D to read the GPA
 * Expected: Access succeeds, VS-stage PTE A-bit is set by HW
 *
 * Note: We use VS=Bare + G=Sv39x4 for simplicity. When VS=Bare,
 * there is no VS-stage translation, so we operate on G-stage PTEs.
 * However, henvcfg.ADUE controls VS-stage A/D updates. To properly
 * test this, we should use VS=Sv39 + G=Sv39x4.
 *
 * For this test, we use VS=Sv39 to properly exercise henvcfg.ADUE.
 * =================================================================== */
TEST_REGISTER(test_hcross_svadu_02);
bool test_hcross_svadu_02(void) {
    TEST_BEGIN("HCROSS-SVADU-02: HLV with Svadu (ADUE=1, A-bit update)");

    if (!H_AVAILABLE) TEST_SKIP("H extension not available");
    if (!SVADU_AVAILABLE) TEST_SKIP("Platform does not implement Svadu");

    two_stage_ctx_t ctx;
    pt_pool_reset();
    gpt_pool_reset();

    /* Setup two-stage: VS=Sv39, G=Sv39x4 */
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    /* Enable ADUE: menvcfg.ADUE=1 + henvcfg.ADUE=1 */
    menvcfg_adue_set(1);
    henvcfg_set_adue(1);

    /* Target VA in test region */
    uintptr_t test_va = (uintptr_t)test_fault_page;

    /* Clear A-bit in VS-stage PTE */
    vs_pte_clear_ad(&ctx, test_va, PT_LEVEL_4K);

    /* Enable two-stage translation so HLV.D walks VS-stage PTEs.
     * Without this, HLV.D uses BARE (identity) and never checks A/D bits. */
    two_stage_enable(&ctx, 0);
    /* Set effective privilege to VS for HLV/HSV instructions.
     * hstatus.SPVP controls HLV/HSV effective privilege (0=VU, 1=VS).
     * VS-stage PTE is S-level (no U bit), so SPVP must be S. */
    hstatus_set_spvp(PRIV_S);

    /* Verify A=0 before HLV */
    uintptr_t pte_before = vs_pte_read(&ctx, test_va, PT_LEVEL_4K);
    TEST_ASSERT("VS-stage PTE A=0 before HLV", (pte_before & PTE_A) == 0);

    /* HS-mode executes HLV.D to read the GPA (identity mapped) */
    trap_expect_begin();
    uint64_t val = hlv_d(test_va);
    (void)val;
    trap_expect_end();

    /* Verify no trap occurred */
    TEST_ASSERT("HLV.D succeeded without trap", !trap_was_triggered());

    /* Verify A-bit was set by hardware */
    uintptr_t pte_after = vs_pte_read(&ctx, test_va, PT_LEVEL_4K);
    TEST_ASSERT("VS-stage PTE A-bit set by HW after HLV", (pte_after & PTE_A) != 0);

    ts2_finish(&ctx);
    HYP_TEST_END();
}

/* ===================================================================
 * HCROSS-SVADU-03: HSV with Svadu (ADUE=1, D-bit HW update)
 *
 * Setup: henvcfg.ADUE=1, VS-stage PTE A=1, D=0
 * Action: HS-mode executes HSV.D to write the GPA
 * Expected: Access succeeds, VS-stage PTE D-bit is set by HW
 * =================================================================== */
TEST_REGISTER(test_hcross_svadu_03);
bool test_hcross_svadu_03(void) {
    TEST_BEGIN("HCROSS-SVADU-03: HSV with Svadu (ADUE=1, D-bit update)");

    if (!H_AVAILABLE) TEST_SKIP("H extension not available");
    if (!SVADU_AVAILABLE) TEST_SKIP("Platform does not implement Svadu");

    two_stage_ctx_t ctx;
    pt_pool_reset();
    gpt_pool_reset();

    /* Setup two-stage: VS=Sv39, G=Sv39x4 */
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    /* Enable ADUE: menvcfg.ADUE=1 + henvcfg.ADUE=1 */
    menvcfg_adue_set(1);
    henvcfg_set_adue(1);

    /* Target VA in test region */
    uintptr_t test_va = (uintptr_t)test_data_area;

    /* Set A=1, D=0 in VS-stage PTE */
    uintptr_t *pte = pt_get_pte(&ctx.vs_ctx, test_va, PT_LEVEL_4K);
    if (pte) {
        *pte = (*pte | PTE_A) & ~PTE_D;
        hfence_vvma_all();
    }

    /* Enable two-stage translation so HSV.D walks VS-stage PTEs. */
    two_stage_enable(&ctx, 0);
    /* Set effective privilege to VS for HLV/HSV instructions. */
    hstatus_set_spvp(PRIV_S);

    /* Verify A=1, D=0 before HSV */
    uintptr_t pte_before = vs_pte_read(&ctx, test_va, PT_LEVEL_4K);
    TEST_ASSERT("VS-stage PTE A=1 before HSV", (pte_before & PTE_A) != 0);
    TEST_ASSERT("VS-stage PTE D=0 before HSV", (pte_before & PTE_D) == 0);

    /* HS-mode executes HSV.D to write the GPA */
    trap_expect_begin();
    hsv_d(test_va, 0xCAFEBABE);
    trap_expect_end();

    /* Verify no trap occurred */
    TEST_ASSERT("HSV.D succeeded without trap", !trap_was_triggered());

    /* Verify D-bit was set by hardware */
    uintptr_t pte_after = vs_pte_read(&ctx, test_va, PT_LEVEL_4K);
    TEST_ASSERT("VS-stage PTE D-bit set by HW after HSV", (pte_after & PTE_D) != 0);

    ts2_finish(&ctx);
    HYP_TEST_END();
}

/* ===================================================================
 * HCROSS-SVADU-04: HLV with Svade (ADUE=0, guest-page-fault)
 *
 * Setup: henvcfg.ADUE=0, VS-stage PTE A=0
 * Action: HS-mode executes HLV.D to read the GPA
 * Expected: guest-page-fault (cause=21), HW does not update A-bit
 * =================================================================== */
TEST_REGISTER(test_hcross_svadu_04);
bool test_hcross_svadu_04(void) {
    TEST_BEGIN("HCROSS-SVADU-04: HLV with Svade (ADUE=0, guest-page-fault)");

    if (!H_AVAILABLE) TEST_SKIP("H extension not available");
    if (!SVADU_AVAILABLE) TEST_SKIP("Platform does not implement Svadu");

    two_stage_ctx_t ctx;
    pt_pool_reset();
    gpt_pool_reset();

    /* Setup two-stage: VS=Sv39, G=Sv39x4 */
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    /* Disable ADUE: menvcfg.ADUE=0 + henvcfg.ADUE=0 */
    menvcfg_adue_set(0);
    henvcfg_set_adue(0);

    /* Target VA in test region */
    uintptr_t test_va = (uintptr_t)test_fault_page;

    /* Clear A-bit in VS-stage PTE */
    vs_pte_clear_ad(&ctx, test_va, PT_LEVEL_4K);

    /* Enable two-stage translation so HLV.D walks VS-stage PTEs. */
    two_stage_enable(&ctx, 0);
    /* Set effective privilege to VS for HLV/HSV instructions. */
    hstatus_set_spvp(PRIV_S);

    /* Verify A=0 before HLV */
    uintptr_t pte_before = vs_pte_read(&ctx, test_va, PT_LEVEL_4K);
    TEST_ASSERT("VS-stage PTE A=0 before HLV", (pte_before & PTE_A) == 0);

    /* HS-mode executes HLV.D to read the GPA */
    trap_expect_begin();
    uint64_t val = hlv_d(test_va);
    (void)val;
    trap_expect_end();

    /* Verify page-fault was triggered.
     * VS-stage translation faults produce page-fault (cause 13), not
     * guest-page-fault (cause 21). Guest-page-faults are only for
     * G-stage translation faults per norm:H_vm_gpatrans. */
    TEST_ASSERT("HLV.D triggered trap", trap_was_triggered());
    if (trap_was_triggered()) {
        TEST_ASSERT_EQ("cause is load page-fault (13)",
                       trap_get_cause(), (uintptr_t)CAUSE_LOAD_PAGE_FAULT);
    }

    /* Verify A-bit was NOT set by hardware (Svade behavior) */
    uintptr_t pte_after = vs_pte_read(&ctx, test_va, PT_LEVEL_4K);
    TEST_ASSERT("VS-stage PTE A-bit NOT set by HW (Svade)", (pte_after & PTE_A) == 0);

    ts2_finish(&ctx);
    HYP_TEST_END();
}

/* ===================================================================
 * HCROSS-SVADU-05: menvcfg.ADUE change + HFENCE.GVMA(x0,x0) sync
 *
 * Setup: menvcfg.ADUE=0, henvcfg.ADUE=1
 * Action: Change menvcfg.ADUE from 0 to 1, first VS-mode access
 *         WITHOUT HFENCE.GVMA (behavior is implementation-dependent);
 *         then execute HFENCE.GVMA(x0,x0) and access again.
 * Expected: First access behavior is implementation-dependent (TLB
 *           may still cache old ADUE=0 interpretation).
 *           After HFENCE.GVMA, access must succeed and A-bit must
 *           be set by HW (new ADUE=1 in effect).
 *
 * Per spec hyp-mm-fences: "if the setting of the PBMTE or ADUE bits
 * in menvcfg are changed, an HFENCE.GVMA instruction with rs1=x0
 * and rs2=x0 suffices to synchronize."
 * =================================================================== */
TEST_REGISTER(test_hcross_svadu_05);
bool test_hcross_svadu_05(void) {
    TEST_BEGIN("HCROSS-SVADU-05: menvcfg.ADUE change + HFENCE.GVMA(x0,x0)");

    if (!H_AVAILABLE) TEST_SKIP("H extension not available");
    if (!SVADU_AVAILABLE) TEST_SKIP("Platform does not implement Svadu");

    two_stage_ctx_t ctx;
    pt_pool_reset();
    gpt_pool_reset();

    /* Setup two-stage: VS=Sv39, G=Sv39x4 */
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    /* Initial: menvcfg.ADUE=0, henvcfg.ADUE=1
     * Note: henvcfg.ADUE is read-only zero when menvcfg.ADUE=0
     * (norm:menvcfg_adue_henvcfg_adue_rdonly0) */
    menvcfg_adue_set(0);
    henvcfg_set_adue(1);

    /* Target VA in test region */
    uintptr_t test_va = (uintptr_t)test_fault_page;

    /* Clear A-bit in VS-stage PTE */
    vs_pte_clear_ad(&ctx, test_va, PT_LEVEL_4K);

    /* Verify A=0 before test */
    uintptr_t pte_before = vs_pte_read(&ctx, test_va, PT_LEVEL_4K);
    TEST_ASSERT("VS-stage PTE A=0 before test", (pte_before & PTE_A) == 0);

    /* Change menvcfg.ADUE from 0 to 1 */
    menvcfg_adue_set(1);

    /* Re-set henvcfg.ADUE=1: when menvcfg.ADUE was 0, henvcfg.ADUE
     * was forced to read-only zero. After enabling menvcfg.ADUE,
     * henvcfg.ADUE must be explicitly set again. */
    henvcfg_set_adue(1);

    /* First VS-mode access WITHOUT HFENCE.GVMA.
     * Behavior is implementation-dependent: TLB may still cache
     * the old ADUE=0 interpretation, causing a fault; or the
     * implementation may immediately pick up the new ADUE=1. */
    uintptr_t result_first = two_stage_run_in_vs(&ctx, probe_load, test_va);
    LOG_I("First access (no HFENCE.GVMA): result=0x%lx (impl-defined)\n",
          (unsigned long)result_first);

    /* Clear A-bit again (in case first access set it) */
    vs_pte_clear_ad(&ctx, test_va, PT_LEVEL_4K);

    /* Execute HFENCE.GVMA(x0,x0) to synchronize across all VMIDs
     * per norm:menvcfg_adue_fence + hyp-mm-fences */
    hfence_gvma_all();

    /* Second VS-mode access - must follow new ADUE=1 */
    uintptr_t result_second = two_stage_run_in_vs(&ctx, probe_load, test_va);
    TEST_ASSERT_EQ("VS-mode load succeeded after HFENCE.GVMA",
                   result_second, (uintptr_t)0);

    /* Verify A-bit was set by hardware */
    uintptr_t pte_after = vs_pte_read(&ctx, test_va, PT_LEVEL_4K);
    TEST_ASSERT("VS-stage PTE A-bit set after HFENCE.GVMA",
                (pte_after & PTE_A) != 0);

    ts2_finish(&ctx);
    HYP_TEST_END();
}

/* ===================================================================
 * HCROSS-SVADU-06: menvcfg.ADUE change + HFENCE.GVMA(vmid,x0) sync
 *
 * Setup: menvcfg.ADUE=1, henvcfg.ADUE=1, pre-populate VMID=6 TLB
 * Action: Change menvcfg.ADUE from 1 to 0, execute HFENCE.GVMA(5,x0)
 * Expected: VMID=5 (HFENCE'd) must follow new ADUE=0 (fault on A=0);
 *           VMID=6 (not HFENCE'd) behavior is implementation-dependent
 *           (TLB may still hold old ADUE=1 interpretation).
 *
 * Per spec hyp-mm-fences: HFENCE.GVMA(vmid,x0) synchronizes only
 * the specified VMID. Other VMIDs may retain cached state.
 * =================================================================== */
TEST_REGISTER(test_hcross_svadu_06);
bool test_hcross_svadu_06(void) {
    TEST_BEGIN("HCROSS-SVADU-06: menvcfg.ADUE change + HFENCE.GVMA(vmid,x0)");

    if (!H_AVAILABLE) TEST_SKIP("H extension not available");
    if (!SVADU_AVAILABLE) TEST_SKIP("Platform does not implement Svadu");

    two_stage_ctx_t ctx;
    pt_pool_reset();
    gpt_pool_reset();

    /* Setup two-stage: VS=Sv39, G=Sv39x4 */
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    /* Initial: menvcfg.ADUE=1, henvcfg.ADUE=1 */
    menvcfg_adue_set(1);
    henvcfg_set_adue(1);

    /* Target VA in test region */
    uintptr_t test_va = (uintptr_t)test_fault_page;

    /* Clear A-bit, HFENCE to ensure clean state */
    vs_pte_clear_ad(&ctx, test_va, PT_LEVEL_4K);
    hfence_gvma_all();

    /* Enable two-stage with VMID=6 (sets both hgatp and vsatp).
     * Subsequent gpt_enable() calls will only change hgatp.VMID,
     * preserving VS-stage TLB entries for other VMIDs.
     * two_stage_enable also does hfence_vvma_all, which is fine
     * here since we are starting from a clean state. */
    two_stage_enable(&ctx, 6);

    /* Pre-populate VMID=6 TLB: access with ADUE=1 succeeds,
     * A-bit set by HW, translation cached in TLB. */
    uintptr_t result_vmid6_pre = run_in_vs_mode(probe_load, test_va);
    TEST_ASSERT_EQ("VMID=6 pre-population access succeeded",
                   result_vmid6_pre, (uintptr_t)0);

    /* Verify A was set by HW during pre-population */
    uintptr_t pte_pre = vs_pte_read(&ctx, test_va, PT_LEVEL_4K);
    TEST_ASSERT("VMID=6 pre-population set A-bit",
                (pte_pre & PTE_A) != 0);

    /* Clear A=0 in PTE memory WITHOUT flushing TLB, so VMID=6's
     * cached TLB entry (with A=1) is preserved. */
    vs_pte_clear_ad_nofence(&ctx, test_va, PT_LEVEL_4K);

    /* Change menvcfg.ADUE from 1 to 0.
     * henvcfg.ADUE becomes read-only zero (forced by menvcfg.ADUE=0). */
    menvcfg_adue_set(0);

    /* HFENCE.GVMA(gpa=0, vmid=5): flush G-stage and VS-stage TLB
     * entries for VMID=5 only. VMID=6's TLB entries are preserved. */
    hfence_gvma(0, 5);

    /* Switch to VMID=5 (only changes hgatp, does not flush TLB). */
    gpt_enable(&ctx.g_ctx, 5);

    /* VMID=5 access: TLB was flushed by HFENCE.GVMA(0,5), so the
     * walker re-walks with new ADUE=0. A=0 must cause fault.
     * Note: probe_load handles traps internally and returns cause on
     * fault, or 0 on success. No outer trap_expect needed. */
    uintptr_t result_vmid5 = run_in_vs_mode(probe_load, test_va);
    TEST_ASSERT_NEQ("VMID=5 access trapped (ADUE=0, HFENCE'd)",
                    result_vmid5, (uintptr_t)0);
    TEST_ASSERT_EQ("VMID=5 cause is load page-fault (VS-stage fault)",
                   result_vmid5, (uintptr_t)CAUSE_LOAD_PAGE_FAULT);

    /* Verify A-bit was NOT set for VMID=5 (faulted, Svade behavior) */
    uintptr_t pte_vmid5 = vs_pte_read(&ctx, test_va, PT_LEVEL_4K);
    TEST_ASSERT("VMID=5 PTE A-bit NOT set (ADUE=0)",
                (pte_vmid5 & PTE_A) == 0);

    /* Switch to VMID=6 (only changes hgatp, does not flush TLB). */
    gpt_enable(&ctx.g_ctx, 6);

    /* VMID=6 access: behavior is implementation-dependent.
     * - If TLB hit (cached from pre-population): access succeeds
     *   without checking A/D bits in PTE.
     * - If TLB miss (implementation invalidated on ADUE change):
     *   walker re-walks with ADUE=0, faults on A=0. */
    uintptr_t result_vmid6 = run_in_vs_mode(probe_load, test_va);
    LOG_I("VMID=6 access (not HFENCE'd): result=0x%lx (impl-defined)\n",
          (unsigned long)result_vmid6);

    ts2_finish(&ctx);
    HYP_TEST_END();
}

/* ===================================================================
 * HCROSS-SVADU-07: henvcfg.ADUE change + HFENCE.VVMA(x0,x0) sync
 *
 * Setup: menvcfg.ADUE=1 (kept enabled), henvcfg.ADUE=1
 * Action: Pre-populate TLB with ADUE=1 (access succeeds, A set by HW);
 *         clear A=0 without TLB flush; change henvcfg.ADUE from 1 to 0;
 *         first access without HFENCE.VVMA (implementation-dependent);
 *         then HFENCE.VVMA(x0,x0) and access again.
 * Expected: First access behavior is implementation-dependent
 *           (TLB may still hold old ADUE=1 interpretation).
 *           After HFENCE.VVMA, access must fault (new ADUE=0 in effect,
 *           A=0, Svade behavior).
 *
 * Per spec hyp-mm-fences: "if the PBMTE or ADUE bits in henvcfg are
 * changed, executing an HFENCE.VVMA with rs1=x0 and rs2=x0 suffices
 * to synchronize with respect to the altered interpretation of
 * VS-stage PTEs' PBMT and A/D bit fields for the currently active VMID."
 * =================================================================== */
TEST_REGISTER(test_hcross_svadu_07);
bool test_hcross_svadu_07(void) {
    TEST_BEGIN("HCROSS-SVADU-07: henvcfg.ADUE change + HFENCE.VVMA(x0,x0)");

    if (!H_AVAILABLE) TEST_SKIP("H extension not available");
    if (!SVADU_AVAILABLE) TEST_SKIP("Platform does not implement Svadu");

    two_stage_ctx_t ctx;
    pt_pool_reset();
    gpt_pool_reset();

    /* Setup two-stage: VS=Sv39, G=Sv39x4 */
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    /* menvcfg.ADUE=1 (keep enabled so henvcfg.ADUE is writable) */
    menvcfg_adue_set(1);
    henvcfg_set_adue(1);

    /* Target VA in test region */
    uintptr_t test_va = (uintptr_t)test_fault_page;

    /* Clear A-bit, enable two-stage (flushes TLB - clean state) */
    vs_pte_clear_ad(&ctx, test_va, PT_LEVEL_4K);
    two_stage_enable(&ctx, 0);

    /* Pre-populate TLB with ADUE=1: access succeeds, A set by HW,
     * translation cached in TLB. */
    uintptr_t result_pre = run_in_vs_mode(probe_load, test_va);
    TEST_ASSERT_EQ("Pre-population access succeeded (ADUE=1)",
                   result_pre, (uintptr_t)0);

    /* Verify A was set by HW */
    uintptr_t pte_pre = vs_pte_read(&ctx, test_va, PT_LEVEL_4K);
    TEST_ASSERT("Pre-population set A-bit (ADUE=1)",
                (pte_pre & PTE_A) != 0);

    /* Clear A=0 in PTE memory WITHOUT flushing TLB, so the cached
     * TLB entry (with A=1) is preserved. */
    vs_pte_clear_ad_nofence(&ctx, test_va, PT_LEVEL_4K);

    /* Change henvcfg.ADUE from 1 to 0 (VS-stage now uses Svade) */
    henvcfg_set_adue(0);

    /* First VS-mode access WITHOUT HFENCE.VVMA.
     * Behavior is implementation-dependent:
     * - TLB hit (cached from pre-population): access succeeds
     *   without checking A/D bits in PTE.
     * - TLB miss (implementation invalidated on ADUE change):
     *   walker re-walks with ADUE=0, faults on A=0. */
    uintptr_t result_first = run_in_vs_mode(probe_load, test_va);
    LOG_I("First access (no HFENCE.VVMA): result=0x%lx (impl-defined)\n",
          (unsigned long)result_first);

    /* Execute HFENCE.VVMA(x0,x0) to synchronize VS-stage TLB
     * for the currently active VMID. */
    hfence_vvma_all();

    /* Second VS-mode access - must follow new ADUE=0.
     * TLB is flushed, so walker re-walks: A=0, ADUE=0 -> fault. */
    uintptr_t result_second = run_in_vs_mode(probe_load, test_va);
    TEST_ASSERT_NEQ("VS-mode load trapped after HFENCE.VVMA (ADUE=0)",
                    result_second, (uintptr_t)0);
    TEST_ASSERT_EQ("Cause is load page-fault after HFENCE.VVMA (VS-stage fault)",
                   result_second, (uintptr_t)CAUSE_LOAD_PAGE_FAULT);

    /* Verify A-bit was NOT set by hardware (Svade behavior) */
    uintptr_t pte_after = vs_pte_read(&ctx, test_va, PT_LEVEL_4K);
    TEST_ASSERT("VS-stage PTE A-bit NOT set after HFENCE.VVMA (ADUE=0)",
                (pte_after & PTE_A) == 0);

    ts2_finish(&ctx);
    HYP_TEST_END();
}
