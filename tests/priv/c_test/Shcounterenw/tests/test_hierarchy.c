/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_hierarchy.c - Group 4: mcounteren/hcounteren/scounteren Hierarchy
 *
 * Tests SHCNTW-HIER-01 through SHCNTW-HIER-05
 * Validates the access control hierarchy:
 *   mcounteren -> hcounteren -> scounteren
 *
 * Key behaviors:
 *   - mcounteren[i]=0: VS-mode access triggers illegal-instruction (cause=2)
 *   - mcounteren[i]=1, hcounteren[i]=0: VS-mode triggers virtual-instruction (cause=22)
 *   - VU-mode needs mcounteren=1, hcounteren=1, scounteren=1 for no-trap access
 *   - VU-mode with hcounteren=0 or scounteren=0: virtual-instruction (cause=22)
 */

/* ------------------------------------------------------------------ */
/* SHCNTW-HIER-01: mcounteren[0]=0 blocks VS-mode cycle access        */
/* ------------------------------------------------------------------ */
TEST_REGISTER(test_shcounterenw_hier_01);
bool test_shcounterenw_hier_01(void) {
    TEST_BEGIN("SHCNTW-HIER-01: mcounteren[0]=0 blocks VS-mode cycle (cause=2)");
    if (!H_AVAILABLE) TEST_SKIP("H-extension not supported");
    if (!is_counter_implemented(0)) TEST_SKIP("cycle not implemented");

    /* mcounteren[0]=0, hcounteren[0]=1 */
    uintptr_t saved_mcen = tsbi_csr_read(CSR_MCOUNTEREN);
    tsbi_csr_clear(CSR_MCOUNTEREN, 1UL << 0);
    uintptr_t saved_hcen = hcounteren_read();
    hcounteren_set(1UL << 0);

    /* VS-mode read cycle — mcounteren=0 triggers illegal-instruction (cause=2) */
    trap_expect_begin();
    run_in_vs_mode(vs_read_cycle, 0);
    TEST_ASSERT("illegal-inst trap triggered", trap_was_triggered());
    if (trap_was_triggered()) {
        TEST_ASSERT_EQ("cause=2 (illegal-instruction)",
                       trap_get_cause(), (uintptr_t)2);
    }
    trap_expect_end();

    /* Restore */
    hcounteren_write(saved_hcen);
    tsbi_csr_write(CSR_MCOUNTEREN, saved_mcen);
    HYP_TEST_END();
}

/* ------------------------------------------------------------------ */
/* SHCNTW-HIER-02: mcounteren[0]=1, hcounteren[0]=1 allows VS-mode    */
/* ------------------------------------------------------------------ */
TEST_REGISTER(test_shcounterenw_hier_02);
bool test_shcounterenw_hier_02(void) {
    TEST_BEGIN("SHCNTW-HIER-02: mcounteren[0]=1, hcounteren[0]=1 allows VS-mode cycle");
    if (!H_AVAILABLE) TEST_SKIP("H-extension not supported");
    if (!is_counter_implemented(0)) TEST_SKIP("cycle not implemented");

    /* mcounteren[0]=1, hcounteren[0]=1 */
    uintptr_t saved_mcen = tsbi_csr_read(CSR_MCOUNTEREN);
    tsbi_csr_set(CSR_MCOUNTEREN, 1UL << 0);
    uintptr_t saved_hcen = hcounteren_read();
    hcounteren_set(1UL << 0);

    /* VS-mode read cycle — should succeed */
    trap_expect_begin();
    run_in_vs_mode(vs_read_cycle, 0);
    TEST_ASSERT("no trap in VS-mode", !trap_was_triggered());
    trap_expect_end();

    /* Restore */
    hcounteren_write(saved_hcen);
    tsbi_csr_write(CSR_MCOUNTEREN, saved_mcen);
    HYP_TEST_END();
}

/* ------------------------------------------------------------------ */
/* SHCNTW-HIER-03: VU-mode: all three layers enabled, reads cycle ok  */
/* ------------------------------------------------------------------ */
TEST_REGISTER(test_shcounterenw_hier_03);
bool test_shcounterenw_hier_03(void) {
    TEST_BEGIN("SHCNTW-HIER-03: VU-mode reads cycle (mcen=1,hcen=1,scen=1)");
    if (!H_AVAILABLE) TEST_SKIP("H-extension not supported");
    if (!is_counter_implemented(0)) TEST_SKIP("cycle not implemented");

    /* mcounteren[0]=1, hcounteren[0]=1, scounteren[0]=1 */
    uintptr_t saved_mcen = tsbi_csr_read(CSR_MCOUNTEREN);
    tsbi_csr_set(CSR_MCOUNTEREN, 1UL << 0);
    uintptr_t saved_hcen = hcounteren_read();
    hcounteren_set(1UL << 0);
    uintptr_t saved_scen = scounteren_read();
    scounteren_set(1UL << 0);

    /* VU-mode read cycle — should succeed */
    trap_expect_begin();
    run_in_vu_mode(vs_read_cycle, 0);
    TEST_ASSERT("no trap in VU-mode", !trap_was_triggered());
    trap_expect_end();

    /* Restore */
    scounteren_write(saved_scen);
    hcounteren_write(saved_hcen);
    tsbi_csr_write(CSR_MCOUNTEREN, saved_mcen);
    HYP_TEST_END();
}

/* ------------------------------------------------------------------ */
/* SHCNTW-HIER-04: VU-mode: hcounteren[0]=0 blocks access (cause=22) */
/* ------------------------------------------------------------------ */
TEST_REGISTER(test_shcounterenw_hier_04);
bool test_shcounterenw_hier_04(void) {
    TEST_BEGIN("SHCNTW-HIER-04: VU-mode cycle blocked by hcounteren[0]=0 (cause=22)");
    if (!H_AVAILABLE) TEST_SKIP("H-extension not supported");
    if (!is_counter_implemented(0)) TEST_SKIP("cycle not implemented");

    /* mcounteren[0]=1, hcounteren[0]=0, scounteren[0]=1 */
    uintptr_t saved_mcen = tsbi_csr_read(CSR_MCOUNTEREN);
    tsbi_csr_set(CSR_MCOUNTEREN, 1UL << 0);
    uintptr_t saved_hcen = hcounteren_read();
    hcounteren_clear(1UL << 0);
    uintptr_t saved_scen = scounteren_read();
    scounteren_set(1UL << 0);

    /* VU-mode read cycle — hcounteren=0 blocks, triggers virtual-inst */
    trap_expect_begin();
    run_in_vu_mode(vs_read_cycle, 0);
    TEST_ASSERT("virtual-inst trap triggered", trap_was_triggered());
    if (trap_was_triggered()) {
        TEST_ASSERT_EQ("cause=22 (virtual-instruction)",
                       trap_get_cause(), (uintptr_t)CAUSE_VIRTUAL_INSTRUCTION);
    }
    trap_expect_end();

    /* Restore */
    scounteren_write(saved_scen);
    hcounteren_write(saved_hcen);
    tsbi_csr_write(CSR_MCOUNTEREN, saved_mcen);
    HYP_TEST_END();
}

/* ------------------------------------------------------------------ */
/* SHCNTW-HIER-05: VU-mode: scounteren[0]=0 blocks access (cause=22) */
/* ------------------------------------------------------------------ */
TEST_REGISTER(test_shcounterenw_hier_05);
bool test_shcounterenw_hier_05(void) {
    TEST_BEGIN("SHCNTW-HIER-05: VU-mode cycle blocked by scounteren[0]=0 (cause=22)");
    if (!H_AVAILABLE) TEST_SKIP("H-extension not supported");
    if (!is_counter_implemented(0)) TEST_SKIP("cycle not implemented");

    /* Pre-check: verify scounteren[0] is writable (can be cleared) */
    uintptr_t saved_scen = scounteren_read();
    scounteren_clear(1UL << 0);
    if ((scounteren_read() & (1UL << 0)) != 0) {
        scounteren_write(saved_scen);
        TEST_SKIP("scounteren[0] is not writable on this platform");
    }
    /* Restore before configuring */
    scounteren_write(saved_scen);

    /* mcounteren[0]=1, hcounteren[0]=1, scounteren[0]=0 */
    uintptr_t saved_mcen = tsbi_csr_read(CSR_MCOUNTEREN);
    tsbi_csr_set(CSR_MCOUNTEREN, 1UL << 0);
    uintptr_t saved_hcen = hcounteren_read();
    hcounteren_set(1UL << 0);
    saved_scen = scounteren_read();
    scounteren_clear(1UL << 0);

    /* VU-mode read cycle — scounteren=0 blocks, triggers virtual-inst */
    trap_expect_begin();
    run_in_vu_mode(vs_read_cycle, 0);
    TEST_ASSERT("virtual-inst trap triggered", trap_was_triggered());
    if (trap_was_triggered()) {
        TEST_ASSERT_EQ("cause=22 (virtual-instruction)",
                       trap_get_cause(), (uintptr_t)CAUSE_VIRTUAL_INSTRUCTION);
    }
    trap_expect_end();

    /* Restore */
    scounteren_write(saved_scen);
    hcounteren_write(saved_hcen);
    tsbi_csr_write(CSR_MCOUNTEREN, saved_mcen);
    HYP_TEST_END();
}
