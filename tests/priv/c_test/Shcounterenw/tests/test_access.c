/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_access.c - Group 2: VS-mode Access Control (End-to-End)
 *
 * Tests SHCNTW-ACCESS-01 through SHCNTW-ACCESS-08
 * Validates that hcounteren bits correctly gate VS-mode access to counters.
 * When hcounteren[i]=0 and mcounteren[i]=1, VS-mode access triggers
 * virtual-instruction exception (cause=22).
 */

/* ------------------------------------------------------------------ */
/* SHCNTW-ACCESS-01: hcounteren[0]=1, VS-mode reads cycle successfully*/
/* ------------------------------------------------------------------ */
TEST_REGISTER(test_shcounterenw_access_01);
bool test_shcounterenw_access_01(void) {
    TEST_BEGIN("SHCNTW-ACCESS-01: VS-mode reads cycle when hcounteren[0]=1");
    if (!H_AVAILABLE) TEST_SKIP("H-extension not supported");
    if (!is_counter_implemented(0)) TEST_SKIP("cycle not implemented");

    /* Configure: mcounteren[0]=1, hcounteren[0]=1 */
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
/* SHCNTW-ACCESS-02: hcounteren[0]=0, VS-mode reads cycle traps       */
/* ------------------------------------------------------------------ */
TEST_REGISTER(test_shcounterenw_access_02);
bool test_shcounterenw_access_02(void) {
    TEST_BEGIN("SHCNTW-ACCESS-02: VS-mode read cycle traps when hcounteren[0]=0");
    if (!H_AVAILABLE) TEST_SKIP("H-extension not supported");
    if (!is_counter_implemented(0)) TEST_SKIP("cycle not implemented");

    /* Configure: mcounteren[0]=1, hcounteren[0]=0 */
    uintptr_t saved_mcen = tsbi_csr_read(CSR_MCOUNTEREN);
    tsbi_csr_set(CSR_MCOUNTEREN, 1UL << 0);
    uintptr_t saved_hcen = hcounteren_read();
    hcounteren_clear(1UL << 0);

    /* VS-mode read cycle — should trigger virtual-instruction exception */
    trap_expect_begin();
    run_in_vs_mode(vs_read_cycle, 0);
    TEST_ASSERT("virtual-inst trap triggered", trap_was_triggered());
    if (trap_was_triggered()) {
        TEST_ASSERT_EQ("cause=22 (virtual-instruction)",
                       trap_get_cause(), (uintptr_t)CAUSE_VIRTUAL_INSTRUCTION);
    }
    trap_expect_end();

    /* Restore */
    hcounteren_write(saved_hcen);
    tsbi_csr_write(CSR_MCOUNTEREN, saved_mcen);
    HYP_TEST_END();
}

/* ------------------------------------------------------------------ */
/* SHCNTW-ACCESS-03: hcounteren[1]=1, VS-mode reads time successfully */
/* ------------------------------------------------------------------ */
TEST_REGISTER(test_shcounterenw_access_03);
bool test_shcounterenw_access_03(void) {
    TEST_BEGIN("SHCNTW-ACCESS-03: VS-mode reads time when hcounteren[1]=1");
    if (!H_AVAILABLE) TEST_SKIP("H-extension not supported");
    if (!is_counter_implemented(1)) TEST_SKIP("time not implemented");

    /* Configure: mcounteren[1]=1, hcounteren[1]=1 */
    uintptr_t saved_mcen = tsbi_csr_read(CSR_MCOUNTEREN);
    tsbi_csr_set(CSR_MCOUNTEREN, 1UL << 1);
    uintptr_t saved_hcen = hcounteren_read();
    hcounteren_set(1UL << 1);

    /* VS-mode read time — should succeed */
    trap_expect_begin();
    run_in_vs_mode(vs_read_time, 0);
    TEST_ASSERT("no trap in VS-mode", !trap_was_triggered());
    trap_expect_end();

    /* Restore */
    hcounteren_write(saved_hcen);
    tsbi_csr_write(CSR_MCOUNTEREN, saved_mcen);
    HYP_TEST_END();
}

/* ------------------------------------------------------------------ */
/* SHCNTW-ACCESS-04: hcounteren[1]=0, VS-mode reads time traps        */
/* ------------------------------------------------------------------ */
TEST_REGISTER(test_shcounterenw_access_04);
bool test_shcounterenw_access_04(void) {
    TEST_BEGIN("SHCNTW-ACCESS-04: VS-mode read time traps when hcounteren[1]=0");
    if (!H_AVAILABLE) TEST_SKIP("H-extension not supported");
    if (!is_counter_implemented(1)) TEST_SKIP("time not implemented");

    /* Configure: mcounteren[1]=1, hcounteren[1]=0 */
    uintptr_t saved_mcen = tsbi_csr_read(CSR_MCOUNTEREN);
    tsbi_csr_set(CSR_MCOUNTEREN, 1UL << 1);
    uintptr_t saved_hcen = hcounteren_read();
    hcounteren_clear(1UL << 1);

    /* VS-mode read time — should trigger virtual-instruction exception */
    trap_expect_begin();
    run_in_vs_mode(vs_read_time, 0);
    TEST_ASSERT("virtual-inst trap triggered", trap_was_triggered());
    if (trap_was_triggered()) {
        TEST_ASSERT_EQ("cause=22 (virtual-instruction)",
                       trap_get_cause(), (uintptr_t)CAUSE_VIRTUAL_INSTRUCTION);
    }
    trap_expect_end();

    /* Restore */
    hcounteren_write(saved_hcen);
    tsbi_csr_write(CSR_MCOUNTEREN, saved_mcen);
    HYP_TEST_END();
}

/* ------------------------------------------------------------------ */
/* SHCNTW-ACCESS-05: hcounteren[2]=1, VS-mode reads instret success   */
/* ------------------------------------------------------------------ */
TEST_REGISTER(test_shcounterenw_access_05);
bool test_shcounterenw_access_05(void) {
    TEST_BEGIN("SHCNTW-ACCESS-05: VS-mode reads instret when hcounteren[2]=1");
    if (!H_AVAILABLE) TEST_SKIP("H-extension not supported");
    if (!is_counter_implemented(2)) TEST_SKIP("instret not implemented");

    /* Configure: mcounteren[2]=1, hcounteren[2]=1 */
    uintptr_t saved_mcen = tsbi_csr_read(CSR_MCOUNTEREN);
    tsbi_csr_set(CSR_MCOUNTEREN, 1UL << 2);
    uintptr_t saved_hcen = hcounteren_read();
    hcounteren_set(1UL << 2);

    /* VS-mode read instret — should succeed */
    trap_expect_begin();
    run_in_vs_mode(vs_read_instret, 0);
    TEST_ASSERT("no trap in VS-mode", !trap_was_triggered());
    trap_expect_end();

    /* Restore */
    hcounteren_write(saved_hcen);
    tsbi_csr_write(CSR_MCOUNTEREN, saved_mcen);
    HYP_TEST_END();
}

/* ------------------------------------------------------------------ */
/* SHCNTW-ACCESS-06: hcounteren[2]=0, VS-mode reads instret traps     */
/* ------------------------------------------------------------------ */
TEST_REGISTER(test_shcounterenw_access_06);
bool test_shcounterenw_access_06(void) {
    TEST_BEGIN("SHCNTW-ACCESS-06: VS-mode read instret traps when hcounteren[2]=0");
    if (!H_AVAILABLE) TEST_SKIP("H-extension not supported");
    if (!is_counter_implemented(2)) TEST_SKIP("instret not implemented");

    /* Configure: mcounteren[2]=1, hcounteren[2]=0 */
    uintptr_t saved_mcen = tsbi_csr_read(CSR_MCOUNTEREN);
    tsbi_csr_set(CSR_MCOUNTEREN, 1UL << 2);
    uintptr_t saved_hcen = hcounteren_read();
    hcounteren_clear(1UL << 2);

    /* VS-mode read instret — should trigger virtual-instruction exception */
    trap_expect_begin();
    run_in_vs_mode(vs_read_instret, 0);
    TEST_ASSERT("virtual-inst trap triggered", trap_was_triggered());
    if (trap_was_triggered()) {
        TEST_ASSERT_EQ("cause=22 (virtual-instruction)",
                       trap_get_cause(), (uintptr_t)CAUSE_VIRTUAL_INSTRUCTION);
    }
    trap_expect_end();

    /* Restore */
    hcounteren_write(saved_hcen);
    tsbi_csr_write(CSR_MCOUNTEREN, saved_mcen);
    HYP_TEST_END();
}

/* ------------------------------------------------------------------ */
/* SHCNTW-ACCESS-07: hcounteren[N]=1, VS-mode reads hpmcounterN ok    */
/* ------------------------------------------------------------------ */
TEST_REGISTER(test_shcounterenw_access_07);
bool test_shcounterenw_access_07(void) {
    TEST_BEGIN("SHCNTW-ACCESS-07: VS-mode reads hpmcounterN when hcounteren[N]=1");
    if (!H_AVAILABLE) TEST_SKIP("H-extension not supported");

    unsigned n = find_first_hpm_counter_gatable();
    if (!n) TEST_SKIP("no hpmcounter with openable mcounteren gate");

    /* Configure: mcounteren[n]=1, hcounteren[n]=1 */
    uintptr_t saved_mcen = tsbi_csr_read(CSR_MCOUNTEREN);
    tsbi_csr_set(CSR_MCOUNTEREN, 1UL << n);
    uintptr_t saved_hcen = hcounteren_read();
    hcounteren_set(1UL << n);

    /* VS-mode read hpmcounterN — should succeed */
    uint16_t csr_addr = counter_csr_addr(n);
    trap_expect_begin();
    run_in_vs_mode(vsmode_read_counter, (uintptr_t)csr_addr);
    TEST_ASSERT("no trap in VS-mode", !trap_was_triggered());
    trap_expect_end();

    /* Restore */
    hcounteren_write(saved_hcen);
    tsbi_csr_write(CSR_MCOUNTEREN, saved_mcen);
    HYP_TEST_END();
}

/* ------------------------------------------------------------------ */
/* SHCNTW-ACCESS-08: hcounteren[N]=0, VS-mode reads hpmcounterN traps */
/* ------------------------------------------------------------------ */
TEST_REGISTER(test_shcounterenw_access_08);
bool test_shcounterenw_access_08(void) {
    TEST_BEGIN("SHCNTW-ACCESS-08: VS-mode read hpmcounterN traps when hcounteren[N]=0");
    if (!H_AVAILABLE) TEST_SKIP("H-extension not supported");

    unsigned n = find_first_hpm_counter_gatable();
    if (!n) TEST_SKIP("no hpmcounter with openable mcounteren gate");

    /* Configure: mcounteren[n]=1, hcounteren[n]=0 */
    uintptr_t saved_mcen = tsbi_csr_read(CSR_MCOUNTEREN);
    tsbi_csr_set(CSR_MCOUNTEREN, 1UL << n);
    uintptr_t saved_hcen = hcounteren_read();
    hcounteren_clear(1UL << n);

    /* VS-mode read hpmcounterN — should trigger virtual-instruction exception */
    uint16_t csr_addr = counter_csr_addr(n);
    trap_expect_begin();
    run_in_vs_mode(vsmode_read_counter, (uintptr_t)csr_addr);
    TEST_ASSERT("virtual-inst trap triggered", trap_was_triggered());
    if (trap_was_triggered()) {
        TEST_ASSERT_EQ("cause=22 (virtual-instruction)",
                       trap_get_cause(), (uintptr_t)CAUSE_VIRTUAL_INSTRUCTION);
    }
    trap_expect_end();

    /* Restore */
    hcounteren_write(saved_hcen);
    tsbi_csr_write(CSR_MCOUNTEREN, saved_mcen);
    HYP_TEST_END();
}
