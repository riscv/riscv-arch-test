/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * common/hyp/tests_2stage/test_group21_hgatp_warl.c
 *
 * Group 21 - hgatp root-page-table alignment and WARL behaviour
 * (TS-HGATP-01..02).
 *
 * Spec basis:
 *   - norm:hgatp_ppn_op:  G-stage root page table is 16 KiB and
 *     must be 16 KiB-aligned. PPN[1:0] always read as zero.
 *   - norm:hgatp_mode_warl: Writing an unsupported MODE is *not*
 *     ignored (unlike satp); it is WARL-handled (the field becomes
 *     some legal value, no exception raised).
 * =================================================================== */

#ifndef SUITE_HGATP_MODE
#error "SUITE_HGATP_MODE must be defined before including this file"
#endif

/* ===================================================================
 * TS-HGATP-01: Writing PPN[1:0]=11 reads back as zero (16KB-align WARL).
 * =================================================================== */
TEST_REGISTER(test_ts_hgatp_01_ppn_low_bits);
bool test_ts_hgatp_01_ppn_low_bits(void) {
    TEST_BEGIN("TS-HGATP-01: hgatp.PPN[1:0] reads back as 0");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t saved = hgatp_read();

    /* Pick a sane PPN inside test memory and OR in the bottom 2 bits.
     * MAKE_HGATP composes mode|vmid|ppn; we then force ppn[1:0]=11. */
    uintptr_t base_ppn = (saved & HGATP_PPN_MASK);
    if (base_ppn == 0) base_ppn = (PLATFORM_MEM_BASE >> 12);
    uintptr_t bad_ppn = base_ppn | 0x3UL;
    uintptr_t probe = MAKE_HGATP(SUITE_HGATP_MODE, /*vmid=*/0, bad_ppn);
    hgatp_write_raw(probe);
    uintptr_t got = hgatp_read();
    hgatp_write_raw(saved);
    hfence_gvma_all();

    uintptr_t got_ppn = HGATP_GET_PPN(got);
    /* Spec mandates PPN[1:0] always read as 0 (16KiB-aligned root PT).
     * A platform that does not enforce this is non-compliant. */
    TEST_ASSERT("hgatp.PPN[0] reads back as 0", (got_ppn & 0x1UL) == 0);
    TEST_ASSERT("hgatp.PPN[1] reads back as 0", (got_ppn & 0x2UL) == 0);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-HGATP-02: Writing an unsupported MODE does not raise an exception
 * and is handled WARL-style (any legal MODE is acceptable on read-back).
 * Reserved encodings: 1..7 and 11..15 (8/9/10 are Sv*x4; 0 is Bare).
 * =================================================================== */
TEST_REGISTER(test_ts_hgatp_02_mode_warl);
bool test_ts_hgatp_02_mode_warl(void) {
    TEST_BEGIN("TS-HGATP-02: unsupported MODE -> WARL, no exception");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t saved = hgatp_read();

    /* Try a reserved MODE encoding (7 is reserved per spec). */
    const unsigned reserved_mode = 7;
    uintptr_t probe = MAKE_HGATP(reserved_mode, /*vmid=*/0, /*ppn=*/0);

    /* The write itself must not trap. We do not arm a trap window
     * because hgatp writes from M-mode never raise illegal-inst by
     * spec; an actual trap would surface as UNEXPECTED. */
    hgatp_write_raw(probe);
    uintptr_t got = hgatp_read();
    unsigned got_mode = (unsigned)((got >> HGATP64_MODE_SHIFT) & 0xFUL);

    /* Restore. */
    hgatp_write_raw(saved);
    hfence_gvma_all();

    /* Per WARL, the read-back MODE must be a legal value: 0 (Bare),
     * 8 (Sv39x4), 9 (Sv48x4), or 10 (Sv57x4). It must NOT remain at
     * the reserved encoding. */
    bool legal = (got_mode == 0) ||
                 (got_mode == HGATP_MODE_SV39X4) ||
                 (got_mode == HGATP_MODE_SV48X4) ||
                 (got_mode == HGATP_MODE_SV57X4);
    TEST_ASSERT("hgatp.MODE read-back is a legal encoding", legal);
    HYP_TEST_END();
}
