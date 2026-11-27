/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_writable.c - Group 1: hcounteren Writability Verification
 *
 * Tests SHCNTW-WR-01 through SHCNTW-WR-05
 * Validates that hcounteren bits corresponding to implemented counters
 * are writable (can be set to 1 and cleared to 0), and that the
 * register itself is 32 bits wide.
 */

/* ------------------------------------------------------------------ */
/* SHCNTW-WR-01: hcounteren[0] writable when cycle is implemented     */
/* ------------------------------------------------------------------ */
TEST_REGISTER(test_shcounterenw_wr_01_cycle);
bool test_shcounterenw_wr_01_cycle(void) {
    TEST_BEGIN("SHCNTW-WR-01: hcounteren[0] writable (cycle)");
    if (!H_AVAILABLE) TEST_SKIP("H-extension not supported");

    if (!is_counter_implemented(0))
        TEST_SKIP("cycle counter not implemented");

    uintptr_t saved = hcounteren_read();

    /* Test: write hcounteren[0] = 1, read back */
    hcounteren_write(saved | (1UL << 0));
    TEST_ASSERT("hcounteren[0] can be set to 1",
                (hcounteren_read() & (1UL << 0)) != 0);

    /* Test: write hcounteren[0] = 0, read back */
    hcounteren_write(hcounteren_read() & ~(1UL << 0));
    TEST_ASSERT("hcounteren[0] can be cleared to 0",
                (hcounteren_read() & (1UL << 0)) == 0);

    /* Restore */
    hcounteren_write(saved);

    TEST_END();
}

/* ------------------------------------------------------------------ */
/* SHCNTW-WR-02: hcounteren[1] writable when time is implemented      */
/* ------------------------------------------------------------------ */
TEST_REGISTER(test_shcounterenw_wr_02_time);
bool test_shcounterenw_wr_02_time(void) {
    TEST_BEGIN("SHCNTW-WR-02: hcounteren[1] writable (time)");
    if (!H_AVAILABLE) TEST_SKIP("H-extension not supported");

    if (!is_counter_implemented(1))
        TEST_SKIP("time counter not implemented");

    uintptr_t saved = hcounteren_read();

    /* Test: write hcounteren[1] = 1, read back */
    hcounteren_write(saved | (1UL << 1));
    TEST_ASSERT("hcounteren[1] can be set to 1",
                (hcounteren_read() & (1UL << 1)) != 0);

    /* Test: write hcounteren[1] = 0, read back */
    hcounteren_write(hcounteren_read() & ~(1UL << 1));
    TEST_ASSERT("hcounteren[1] can be cleared to 0",
                (hcounteren_read() & (1UL << 1)) == 0);

    /* Restore */
    hcounteren_write(saved);

    TEST_END();
}

/* ------------------------------------------------------------------ */
/* SHCNTW-WR-03: hcounteren[2] writable when instret is implemented   */
/* ------------------------------------------------------------------ */
TEST_REGISTER(test_shcounterenw_wr_03_instret);
bool test_shcounterenw_wr_03_instret(void) {
    TEST_BEGIN("SHCNTW-WR-03: hcounteren[2] writable (instret)");
    if (!H_AVAILABLE) TEST_SKIP("H-extension not supported");

    if (!is_counter_implemented(2))
        TEST_SKIP("instret counter not implemented");

    uintptr_t saved = hcounteren_read();

    /* Test: write hcounteren[2] = 1, read back */
    hcounteren_write(saved | (1UL << 2));
    TEST_ASSERT("hcounteren[2] can be set to 1",
                (hcounteren_read() & (1UL << 2)) != 0);

    /* Test: write hcounteren[2] = 0, read back */
    hcounteren_write(hcounteren_read() & ~(1UL << 2));
    TEST_ASSERT("hcounteren[2] can be cleared to 0",
                (hcounteren_read() & (1UL << 2)) == 0);

    /* Restore */
    hcounteren_write(saved);

    TEST_END();
}

/* ------------------------------------------------------------------ */
/* SHCNTW-WR-04: hcounteren[3:31] writable for implemented hpmcounters*/
/* ------------------------------------------------------------------ */
TEST_REGISTER(test_shcounterenw_wr_04_hpm);
bool test_shcounterenw_wr_04_hpm(void) {
    TEST_BEGIN("SHCNTW-WR-04: hcounteren[3:31] writable (hpmcounters)");
    if (!H_AVAILABLE) TEST_SKIP("H-extension not supported");

    uintptr_t saved = hcounteren_read();
    bool found_any = false;

    for (unsigned i = SHCNTW_FIRST_HPM; i <= SHCNTW_LAST_HPM; i++) {
        if (!is_counter_implemented(i))
            continue;
        found_any = true;

        /* Test: write hcounteren[i] = 1, read back */
        hcounteren_write(hcounteren_read() | (1UL << i));
        uintptr_t readback = hcounteren_read();
        if ((readback & (1UL << i)) == 0) {
            LOG_E("hpmcounter%u: hcounteren[%u] failed to set\n", i, i);
            TEST_ASSERT("hcounteren bit set", false);
        }

        /* Test: write hcounteren[i] = 0, read back */
        hcounteren_write(hcounteren_read() & ~(1UL << i));
        readback = hcounteren_read();
        if ((readback & (1UL << i)) != 0) {
            LOG_E("hpmcounter%u: hcounteren[%u] failed to clear\n", i, i);
            TEST_ASSERT("hcounteren bit clear", false);
        }
    }

    /* Restore */
    hcounteren_write(saved);

    if (!found_any) TEST_SKIP("no hpmcounter3-31 implemented");
    TEST_ASSERT("all implemented hpmcounter hcounteren bits writable", true);

    TEST_END();
}

/* ------------------------------------------------------------------ */
/* SHCNTW-WR-05: hcounteren is a 32-bit register (upper bits RO zero) */
/* ------------------------------------------------------------------ */
TEST_REGISTER(test_shcounterenw_wr_05_width);
bool test_shcounterenw_wr_05_width(void) {
    TEST_BEGIN("SHCNTW-WR-05: hcounteren upper 32 bits read-only zero");
    if (!H_AVAILABLE) TEST_SKIP("H-extension not supported");
#if __riscv_xlen == 64
    uintptr_t saved = hcounteren_read();

    /* norm:hcounteren_sz: hcounteren is a 32-bit register. On RV64
     * an all-ones write must not take effect in bits 63:32. */
    hcounteren_write(~0UL);
    uintptr_t readback = hcounteren_read();
    TEST_ASSERT_EQ("hcounteren bits 63:32 read-only zero",
                   readback & ~0xFFFFFFFFUL, (uintptr_t)0);

    /* Restore */
    hcounteren_write(saved);
#else
    TEST_SKIP("32-bit width check only meaningful on RV64");
#endif

    TEST_END();
}
