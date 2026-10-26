/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 5: hgatp PPN field low 2-bit behavior
 *
 * Spec anchors:
 *   norm:hgatp_ppn_op (hypervisor.adoc:1078-1085):
 *     In Sv*x4 modes, hgatp.PPN[1:0] always read zero (root page
 *     table must be 16KB-aligned).
 *
 * Test list (matches DOCS/testplan/shgatpa_test_plan.md HGATP-PPN):
 *   HGATP-PPN-01  Sv39x4 PPN[1:0]=0b11 forced to zero
 *   HGATP-PPN-02  Sv39x4 PPN high bits preserved
 *   HGATP-PPN-03  Sv48x4 PPN[1:0] forced to zero
 *
 * NOTE: hgatp_write_raw() is used to bypass the framework's software
 * PPN masking, so we can observe the actual hardware behavior.
 * =================================================================== */

extern volatile bool g_satp_supports_sv39;
extern volatile bool g_satp_supports_sv48;

/* ---- HGATP-PPN-01 ---- */
TEST_REGISTER(test_shgatpa_ppn_low2_sv39x4);
bool test_shgatpa_ppn_low2_sv39x4(void) {
    TEST_BEGIN("HGATP-PPN-01: Sv39x4 mode PPN[1:0] forced to zero");

    if (!g_satp_supports_sv39) {
        TEST_SKIP("satp does not support Sv39, Sv39x4 unavailable");
    }

    uintptr_t saved = hgatp_read();

    /* Write Sv39x4 + PPN with low 2 bits = 0b11 */
    hgatp_write_raw(MAKE_HGATP(HGATP_MODE_SV39X4, 0, 0x2003));
    uintptr_t ppn = HGATP_GET_PPN(hgatp_read());

    TEST_ASSERT_EQ("hgatp.PPN[1:0] == 0 in Sv39x4 mode",
                   ppn & 0x3UL, 0UL);
    TEST_ASSERT_EQ("hgatp.PPN high bits preserved (0x2000)",
                   ppn & ~0x3UL, 0x2000UL);

    hgatp_write_raw(saved);
    HYP_TEST_END();
}

/* ---- HGATP-PPN-02 ---- */
TEST_REGISTER(test_shgatpa_ppn_high_preserved);
bool test_shgatpa_ppn_high_preserved(void) {
    TEST_BEGIN("HGATP-PPN-02: Sv39x4 mode PPN high bits preserved");

    if (!g_satp_supports_sv39) {
        TEST_SKIP("satp does not support Sv39, Sv39x4 unavailable");
    }

    uintptr_t saved = hgatp_read();

    /* Write Sv39x4 + PPN = 0x12340 (low 2 bits already 0) */
    hgatp_write_raw(MAKE_HGATP(HGATP_MODE_SV39X4, 0, 0x12340));
    uintptr_t ppn = HGATP_GET_PPN(hgatp_read());

    TEST_ASSERT_EQ("hgatp.PPN == 0x12340 (high bits preserved, low 2 zero)",
                   ppn, 0x12340UL);

    hgatp_write_raw(saved);
    HYP_TEST_END();
}

/* ---- HGATP-PPN-03 ---- */
TEST_REGISTER(test_shgatpa_ppn_low2_sv48x4);
bool test_shgatpa_ppn_low2_sv48x4(void) {
    TEST_BEGIN("HGATP-PPN-03: Sv48x4 mode PPN[1:0] forced to zero");

    if (!g_satp_supports_sv48) {
        TEST_SKIP("satp does not support Sv48, Sv48x4 unavailable");
    }

    uintptr_t saved = hgatp_read();

    /* Write Sv48x4 + PPN with low bit = 01 */
    hgatp_write_raw(MAKE_HGATP(HGATP_MODE_SV48X4, 0, 0x5001));
    uintptr_t ppn = HGATP_GET_PPN(hgatp_read());

    TEST_ASSERT_EQ("hgatp.PPN[1:0] == 0 in Sv48x4 mode",
                   ppn & 0x3UL, 0UL);

    hgatp_write_raw(saved);
    HYP_TEST_END();
}
