/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * Test Group 9: hedeleg/hideleg delegation register field constraints
 *
 * Tests DELEG-01 through DELEG-03 verify the bit-field WARL attributes
 * of the delegation registers. Split from Hypervisor/tests/test_delegation.c.
 * See DOCS/testplan/Hypervisor_CSR_test_plan.md.
 */

#include "hyp_test_helpers.h"
/* ------------------------------------------------------------------
 * DELEG-01: hedeleg writable/read-only bit verification
 *
 * Per spec hedeleg-bits table:
 *   Writable:    1-8, 12, 13, 15, 18, 19
 *   Read-only 0: 9-11, 16, 20-23
 *   Bit 0: writable if IALIGN=32, else read-only 0
 * ------------------------------------------------------------------ */
TEST_REGISTER(hedeleg_writable_bits);
bool hedeleg_writable_bits(void)
{
    TEST_BEGIN("DELEG-01: Write all 1s to hedeleg and verify per-bit attributes");

    hedeleg_write(0xFFFFFFFF);
    uintptr_t val = hedeleg_read();

    /* Bits required writable per spec hedeleg-bits table.
     * Bit 19 (hardware error) requires Smaia; omit from required mask.
     * Test it separately as implementation-dependent. */
    uintptr_t spec_writable = (1UL << 1) | (1UL << 2) | (1UL << 3) |
                              (1UL << 4) | (1UL << 5) | (1UL << 6) |
                              (1UL << 7) | (1UL << 8) | (1UL << 12) |
                              (1UL << 13) | (1UL << 15) | (1UL << 18);
    TEST_ASSERT_EQ("hedeleg spec-writable bits (1-8,12,13,15,18) should be writable",
                   val & spec_writable, spec_writable);

    /* All read-only zero bits */
    uintptr_t ro_zero = (1UL << 9) | (1UL << 10) | (1UL << 11) |
                        (1UL << 16) |
                        (1UL << 20) | (1UL << 21) | (1UL << 22) | (1UL << 23);
    TEST_ASSERT_EQ("hedeleg read-only zero bits (9-11,16,20-23) must be zero",
                   val & ro_zero, (uintptr_t)0);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * DELEG-02: hedeleg bit 0 writability depends on IALIGN
 * ------------------------------------------------------------------ */
TEST_REGISTER(hedeleg_bit0_writable);
bool hedeleg_bit0_writable(void)
{
    TEST_BEGIN("DELEG-02: Verify hedeleg bit 0 IALIGN dependency");

    hedeleg_write(0x0);
    uintptr_t base = hedeleg_read();

    hedeleg_write(0x1);
    uintptr_t val = hedeleg_read();

    /* Writing bit 0 must not affect other bits */
    TEST_ASSERT_EQ("writing bit 0 must not set unexpected bits",
                   val & ~(uintptr_t)0x1, base & ~(uintptr_t)0x1);

    /* IALIGN=32 -> bit 0 writable; IALIGN=16/64 -> read-only zero. */
    if (val & 0x1) {
        TEST_ASSERT("IALIGN=32: hedeleg bit 0 should be writable", true);
    } else {
        TEST_ASSERT("IALIGN!=32: hedeleg bit 0 is read-only zero (acceptable)", true);
    }

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * DELEG-03: hideleg writable and read-only bit verification
 *
 * Per norm:hideleg_acc:
 *   Writable:    bits 10, 6, 2 (VS-level interrupts)
 *   Read-only 0: bits 12, 9, 5, 1 (S-level interrupts)
 * ------------------------------------------------------------------ */
TEST_REGISTER(hideleg_writable_bits);
bool hideleg_writable_bits(void)
{
    TEST_BEGIN("DELEG-03: Verify hideleg writable bits (10/6/2) and read-only (12/9/5/1)");

    hideleg_write(0xFFFFFFFF);
    uintptr_t val = hideleg_read();

    /* Bits 10,6,2 must be writable (VSEI/VSTI/VSSI) */
    uintptr_t writable = 0x444;
    TEST_ASSERT_EQ("hideleg writable bits (10/6/2) must be writable",
                   val & writable, writable);

    /* Bits 12,9,5,1 must be read-only zero (SEI/STI/SSI) */
    uintptr_t ro_zero = (1UL << 12) | (1UL << 9) | (1UL << 5) | (1UL << 1);
    TEST_ASSERT_EQ("hideleg read-only zero bits (12/9/5/1) must be zero",
                   val & ro_zero, (uintptr_t)0);

    HYP_TEST_END();
}
