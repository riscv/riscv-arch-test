/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * Test Group 4: htimedelta time offset
 *
 * Tests HTDLT-01 through HTDLT-05 verify htimedelta register behavior.
 *
 * Spec basis:
 *   norm:htimedelta_sz_acc_op - 64-bit RW register; VS/VU-mode reads
 *     of time return time + htimedelta.
 *   norm:time_htimedelta_req  - If time CSR is implemented, htimedelta
 *     must be implemented.
 */

#include "hyp_test_helpers.h"

/* ------------------------------------------------------------------
 * HTDLT-01: htimedelta basic read/write
 *
 * HS-mode writes htimedelta=0x1000 and reads it back.
 * Expected: read-back value equals 0x1000.
 * ------------------------------------------------------------------ */
TEST_REGISTER(htimedelta_basic_rw);
bool htimedelta_basic_rw(void)
{
    TEST_BEGIN("HTDLT-01: Verify htimedelta basic read/write");

    /* Write 0x1000 to htimedelta. */
    htimedelta_set(0x1000);
    uintptr_t val;
    val = CSRR(CSR_HTIMEDELTA);

    /* Verify value is written. */
    TEST_ASSERT_EQ("htimedelta should read back 0x1000", val, 0x1000);

    htimedelta_set(0); /* Restore */

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * HTDLT-02: VS-mode reads time with delta applied
 *
 * Set htimedelta=N, VS-mode reads time CSR.
 * Expected: returned value ~= real time + N.
 * ------------------------------------------------------------------ */
TEST_REGISTER(htimedelta_affects_vs_time);
bool htimedelta_affects_vs_time(void)
{
    TEST_BEGIN("HTDLT-02: Verify VS-mode reads time with delta applied");

    /* Allow VS-mode to access time CSR.
     * mcounteren.TM gates S/HS access; hcounteren.TM gates VS access. */
    uintptr_t saved_mcen = tsbi_csr_read(CSR_MCOUNTEREN);
    tsbi_csr_set(CSR_MCOUNTEREN, 0x2); /* TM bit */
    uintptr_t saved_hcen = hcounteren_read();
    hcounteren_set(0x2); /* TM bit */

    /* Set htimedelta to a known offset. */
    uintptr_t delta = 100000;
    htimedelta_set(delta);

    /* Read real time from HS-mode. */
    uintptr_t hs_time;
    hs_time = CSRR(CSR_TIME);

    /* Read time from VS-mode (should be hs_time + delta). */
    uintptr_t vs_time = run_in_vs_mode(vs_read_time, 0);

    /* VS time should be approximately hs_time + delta.
     * Allow slack for instruction execution time. */
    int64_t diff = (int64_t)(vs_time - hs_time);
    TEST_ASSERT("VS time ~= HS time + delta (approx)",
                diff >= (int64_t)(delta - 1000) &&
                diff <= (int64_t)(delta + 100000));

    htimedelta_set(0); /* Restore */
    hcounteren_write(saved_hcen);
    tsbi_csr_write(CSR_MCOUNTEREN, saved_mcen);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * HTDLT-03: VU-mode reads time with delta applied
 *
 * Set htimedelta=N, VU-mode reads time CSR.
 * Expected: returned value ~= real time + N.
 *
 * For VU-mode counter access, three gates must all permit TM:
 *   mcounteren.TM = 1  (M-mode gate)
 *   hcounteren.TM = 1  (HS-mode gate for VS/VU)
 *   scounteren.TM = 1  (maps to vcounteren.TM when V=1, gates VU)
 * ------------------------------------------------------------------ */
TEST_REGISTER(htimedelta_affects_vu_time);
bool htimedelta_affects_vu_time(void)
{
    TEST_BEGIN("HTDLT-03: Verify VU-mode reads time with delta applied");

    /* Save and configure counter-enable gates for VU-mode time access. */
    uintptr_t saved_mcen = tsbi_csr_read(CSR_MCOUNTEREN);
    tsbi_csr_set(CSR_MCOUNTEREN, 0x2); /* mcounteren.TM */
    uintptr_t saved_hcen = hcounteren_read();
    hcounteren_set(0x2); /* hcounteren.TM */
    uintptr_t saved_scen = scounteren_read();
    scounteren_set(0x2); /* scounteren.TM -> vcounteren.TM when V=1 */

    /* Set htimedelta to a known offset. */
    uintptr_t delta = 100000;
    htimedelta_set(delta);

    /* Read real time from HS-mode. */
    uintptr_t hs_time;
    hs_time = CSRR(CSR_TIME);

    /* Read time from VU-mode (should be hs_time + delta). */
    uintptr_t vu_time = run_in_vu_mode(vs_read_time, 0);

    /* VU time should be approximately hs_time + delta.
     * Allow slack for instruction execution time. */
    int64_t diff = (int64_t)(vu_time - hs_time);
    TEST_ASSERT("VU time ~= HS time + delta (approx)",
                diff >= (int64_t)(delta - 1000) &&
                diff <= (int64_t)(delta + 100000));

    htimedelta_set(0); /* Restore */
    scounteren_write(saved_scen);
    hcounteren_write(saved_hcen);
    tsbi_csr_write(CSR_MCOUNTEREN, saved_mcen);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * HTDLT-04: htimedelta large value (negative offset / wrap-around)
 *
 * Set htimedelta = 0xFFFFFFFFFFFF0000 (near 2^64, equivalent to a
 * negative offset of -65536 in 64-bit modular arithmetic).
 *
 * Expected: VS-mode reads time and the 64-bit truncated sum
 * (time + htimedelta) wraps around, yielding a value SMALLER than
 * the real time.
 * ------------------------------------------------------------------ */
TEST_REGISTER(htimedelta_large_value_negative_offset);
bool htimedelta_large_value_negative_offset(void)
{
    TEST_BEGIN("HTDLT-04: Verify htimedelta large value causes wrap-around");

    /* Allow VS-mode to access time CSR. */
    uintptr_t saved_mcen = tsbi_csr_read(CSR_MCOUNTEREN);
    tsbi_csr_set(CSR_MCOUNTEREN, 0x2); /* TM bit */
    uintptr_t saved_hcen = hcounteren_read();
    hcounteren_set(0x2); /* TM bit */

    /* Set htimedelta to a near-max value (negative offset). */
    uint64_t large_delta = 0xFFFFFFFFFFFF0000ULL;
    htimedelta_set(large_delta);

    /* Verify the large value is stored correctly. */
    uintptr_t readback;
    readback = CSRR(CSR_HTIMEDELTA);
    TEST_ASSERT_EQ("htimedelta should hold 0xFFFFFFFFFFFF0000",
                   readback, (uintptr_t)large_delta);

    /* Read real time from HS-mode. */
    uintptr_t hs_time;
    hs_time = CSRR(CSR_TIME);

    /* Read time from VS-mode.
     * With delta = 0xFFFFFFFFFFFF0000 (= -65536 mod 2^64),
     * VS time = (hs_time + delta) mod 2^64 should wrap around
     * and be significantly less than hs_time. */
    uintptr_t vs_time = run_in_vs_mode(vs_read_time, 0);

    int64_t diff = (int64_t)(vs_time - hs_time);
    /* diff should be approximately -65536 (negative due to wrap).
     * Allow wide tolerance for execution time between reads. */
    TEST_ASSERT("VS time < HS time (negative offset via wrap-around)",
                diff < -1000 && diff > -200000);

    htimedelta_set(0); /* Restore */
    hcounteren_write(saved_hcen);
    tsbi_csr_write(CSR_MCOUNTEREN, saved_mcen);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * HTDLT-05: HS-mode reads time without delta
 *
 * Set htimedelta=N, HS-mode reads time CSR.
 * Expected: HS-mode returns real time (delta NOT applied).
 *
 * Per spec, htimedelta only affects VS-mode and VU-mode reads of
 * the time CSR.  HS-mode (V=0) must observe the real time.
 * ------------------------------------------------------------------ */
TEST_REGISTER(htimedelta_hs_mode_no_delta);
bool htimedelta_hs_mode_no_delta(void)
{
    TEST_BEGIN("HTDLT-05: Verify HS-mode reads time without delta");

    /* Set htimedelta to a non-trivial offset. */
    uintptr_t delta = 100000;
    htimedelta_set(delta);

    /* Read time twice from HS-mode and also capture a reference
     * VS-mode read to confirm delta is active. */
    uintptr_t hs_time1;
    hs_time1 = CSRR(CSR_TIME);

    uintptr_t hs_time2;
    hs_time2 = CSRR(CSR_TIME);

    /* HS time must be monotonically non-decreasing. */
    TEST_ASSERT("HS time is monotonically non-decreasing",
                hs_time2 >= hs_time1);

    /* The two HS reads should be very close (no delta applied).
     * If delta were erroneously applied, the difference between
     * consecutive reads would be on the order of delta, not a
     * few hundred cycles. */
    uintptr_t hs_diff = hs_time2 - hs_time1;
    TEST_ASSERT("HS time reads are close together (no delta effect)",
                hs_diff < 10000);

    /* Cross-check: VS-mode should see time shifted by delta,
     * proving the delta IS active and HS-mode is immune. */
    uintptr_t saved_mcen = tsbi_csr_read(CSR_MCOUNTEREN);
    tsbi_csr_set(CSR_MCOUNTEREN, 0x2);
    uintptr_t saved_hcen = hcounteren_read();
    hcounteren_set(0x2);

    uintptr_t hs_time3;
    hs_time3 = CSRR(CSR_TIME);
    uintptr_t vs_time = run_in_vs_mode(vs_read_time, 0);

    int64_t vs_hs_diff = (int64_t)(vs_time - hs_time3);
    TEST_ASSERT("VS time is offset by delta (confirms delta active)",
                vs_hs_diff >= (int64_t)(delta - 1000) &&
                vs_hs_diff <= (int64_t)(delta + 100000));

    htimedelta_set(0); /* Restore */
    hcounteren_write(saved_hcen);
    tsbi_csr_write(CSR_MCOUNTEREN, saved_mcen);

    HYP_TEST_END();
}
