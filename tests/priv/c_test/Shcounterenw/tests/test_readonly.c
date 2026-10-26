/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_readonly.c - Group 5: Read-Only Zero Counter Report
 *
 * Test SHCNTW-RO-01
 * For hpmcounters that are read-only zero, report whether the
 * corresponding hcounteren bit is writable or hardwired.
 * This is informational only — always passes.
 */

/* ------------------------------------------------------------------ */
/* SHCNTW-RO-01: Report hcounteren bits for read-only-zero counters   */
/* ------------------------------------------------------------------ */
TEST_REGISTER(test_shcounterenw_ro_01_report);
bool test_shcounterenw_ro_01_report(void) {
    TEST_BEGIN("SHCNTW-RO-01: hcounteren bits for read-only-zero counters");
    if (!H_AVAILABLE) TEST_SKIP("H-extension not supported");

    uintptr_t saved_hcen = hcounteren_read();
    unsigned ro_count = 0;

    LOG_I("Scanning hpmcounter3-31 for read-only-zero counters...\n");

    for (unsigned i = SHCNTW_FIRST_HPM; i <= SHCNTW_LAST_HPM; i++) {
        /* Check if this counter is implemented (non-read-only-zero) */
        if (is_counter_implemented(i))
            continue;

        /* This counter is read-only zero (or unimplemented) */
        ro_count++;

        /* Try to set hcounteren[i]=1 */
        hcounteren_write(hcounteren_read() | (1UL << i));
        bool can_set = (hcounteren_read() & (1UL << i)) != 0;

        /* Try to clear hcounteren[i]=0 */
        hcounteren_write(hcounteren_read() & ~(1UL << i));
        bool can_clear = (hcounteren_read() & (1UL << i)) == 0;

        const char *behavior;
        if (can_set && can_clear)
            behavior = "writable (RW)";
        else if (!can_set && can_clear)
            behavior = "hardwired to 0";
        else if (can_set && !can_clear)
            behavior = "hardwired to 1";
        else
            behavior = "unknown";

        LOG_D("hpmcounter%u: read-only zero, hcounteren[%u] %s\n",
              i, i, behavior);
    }

    hcounteren_write(saved_hcen);

    if (ro_count == 0)
        LOG_I("No read-only-zero hpmcounters found (all implemented).\n");
    else
        LOG_I("Total read-only-zero counters: %u\n", ro_count);

    /* Informational test — always passes */
    TEST_ASSERT("read-only zero counter report completed", true);

    TEST_END();
}
