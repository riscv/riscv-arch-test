/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_toggle.c - Group 3: hcounteren Bit Toggle Consistency
 *
 * Tests SHCNTW-TOGGLE-01 through SHCNTW-TOGGLE-03
 * Validates that hcounteren bits can be toggled repeatedly and
 * VS-mode access behavior matches the current bit value each time.
 */

/* ------------------------------------------------------------------ */
/* SHCNTW-TOGGLE-01: cycle bit toggle consistency                     */
/* ------------------------------------------------------------------ */
TEST_REGISTER(test_shcounterenw_toggle_01_cycle);
bool test_shcounterenw_toggle_01_cycle(void) {
    TEST_BEGIN("SHCNTW-TOGGLE-01: hcounteren[0] toggle consistency (cycle)");
    if (!H_AVAILABLE) TEST_SKIP("H-extension not supported");
    if (!is_counter_implemented(0)) TEST_SKIP("cycle not implemented");

    /* Ensure mcounteren[0]=1 so hcounteren layer controls access */
    uintptr_t saved_mcen = tsbi_csr_read(CSR_MCOUNTEREN);
    tsbi_csr_set(CSR_MCOUNTEREN, 1UL << 0);
    uintptr_t saved_hcen = hcounteren_read();

    for (int i = 0; i < 4; i++) {
        bool enable = (i % 2 == 0);

        if (enable)
            hcounteren_set(1UL << 0);
        else
            hcounteren_clear(1UL << 0);

        trap_expect_begin();
        run_in_vs_mode(vs_read_cycle, 0);

        if (enable) {
            TEST_ASSERT("cycle accessible after enable",
                        !trap_was_triggered());
        } else {
            TEST_ASSERT("cycle blocked after disable",
                        trap_was_triggered());
            if (trap_was_triggered()) {
                TEST_ASSERT_EQ("cause=22",
                               trap_get_cause(),
                               (uintptr_t)CAUSE_VIRTUAL_INSTRUCTION);
            }
        }
        trap_expect_end();
    }

    hcounteren_write(saved_hcen);
    tsbi_csr_write(CSR_MCOUNTEREN, saved_mcen);
    HYP_TEST_END();
}

/* ------------------------------------------------------------------ */
/* SHCNTW-TOGGLE-02: instret bit toggle consistency                   */
/* ------------------------------------------------------------------ */
TEST_REGISTER(test_shcounterenw_toggle_02_instret);
bool test_shcounterenw_toggle_02_instret(void) {
    TEST_BEGIN("SHCNTW-TOGGLE-02: hcounteren[2] toggle consistency (instret)");
    if (!H_AVAILABLE) TEST_SKIP("H-extension not supported");
    if (!is_counter_implemented(2)) TEST_SKIP("instret not implemented");

    /* Ensure mcounteren[2]=1 */
    uintptr_t saved_mcen = tsbi_csr_read(CSR_MCOUNTEREN);
    tsbi_csr_set(CSR_MCOUNTEREN, 1UL << 2);
    uintptr_t saved_hcen = hcounteren_read();

    for (int i = 0; i < 4; i++) {
        bool enable = (i % 2 == 0);

        if (enable)
            hcounteren_set(1UL << 2);
        else
            hcounteren_clear(1UL << 2);

        trap_expect_begin();
        run_in_vs_mode(vs_read_instret, 0);

        if (enable) {
            TEST_ASSERT("instret accessible after enable",
                        !trap_was_triggered());
        } else {
            TEST_ASSERT("instret blocked after disable",
                        trap_was_triggered());
            if (trap_was_triggered()) {
                TEST_ASSERT_EQ("cause=22",
                               trap_get_cause(),
                               (uintptr_t)CAUSE_VIRTUAL_INSTRUCTION);
            }
        }
        trap_expect_end();
    }

    hcounteren_write(saved_hcen);
    tsbi_csr_write(CSR_MCOUNTEREN, saved_mcen);
    HYP_TEST_END();
}

/* ------------------------------------------------------------------ */
/* SHCNTW-TOGGLE-03: hpmcounterN bit toggle consistency               */
/* ------------------------------------------------------------------ */
TEST_REGISTER(test_shcounterenw_toggle_03_hpm);
bool test_shcounterenw_toggle_03_hpm(void) {
    TEST_BEGIN("SHCNTW-TOGGLE-03: hcounteren[N] toggle consistency (hpmcounterN)");
    if (!H_AVAILABLE) TEST_SKIP("H-extension not supported");

    unsigned n = find_first_hpm_counter_gatable();
    if (!n) TEST_SKIP("no hpmcounter with openable mcounteren gate");

    /* Ensure mcounteren[n]=1 */
    uintptr_t saved_mcen = tsbi_csr_read(CSR_MCOUNTEREN);
    tsbi_csr_set(CSR_MCOUNTEREN, 1UL << n);
    uintptr_t saved_hcen = hcounteren_read();
    uint16_t csr_addr = counter_csr_addr(n);

    for (int i = 0; i < 4; i++) {
        bool enable = (i % 2 == 0);

        if (enable)
            hcounteren_set(1UL << n);
        else
            hcounteren_clear(1UL << n);

        trap_expect_begin();
        run_in_vs_mode(vsmode_read_counter, (uintptr_t)csr_addr);

        if (enable) {
            TEST_ASSERT("hpmcounterN accessible after enable",
                        !trap_was_triggered());
        } else {
            TEST_ASSERT("hpmcounterN blocked after disable",
                        trap_was_triggered());
            if (trap_was_triggered()) {
                TEST_ASSERT_EQ("cause=22",
                               trap_get_cause(),
                               (uintptr_t)CAUSE_VIRTUAL_INSTRUCTION);
            }
        }
        trap_expect_end();
    }

    hcounteren_write(saved_hcen);
    tsbi_csr_write(CSR_MCOUNTEREN, saved_mcen);
    HYP_TEST_END();
}
