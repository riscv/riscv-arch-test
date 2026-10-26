/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 3: hgatp Bare mode mandatory support
 *
 * Spec anchors:
 *   norm:shgatpa_hgatp_bare_mode (shgatpa.adoc:9-10)
 *   norm:hgatp_mode_bare         (hypervisor.adoc:1010-1015)
 *
 * Test list (matches DOCS/testplan/shgatpa_test_plan.md HGATP-BARE):
 *   HGATP-BARE-01  hgatp MODE=Bare write/readback
 *   HGATP-BARE-02  hgatp switch from SvNNx4 back to Bare
 *   HGATP-BARE-03  hgatp Bare mode PPN/VMID zero
 * =================================================================== */

extern volatile bool g_satp_supports_sv39;

/* ---- HGATP-BARE-01 ---- */
TEST_REGISTER(test_shgatpa_bare_readback);
bool test_shgatpa_bare_readback(void) {
    TEST_BEGIN("HGATP-BARE-01: hgatp MODE=Bare write/readback");

    uintptr_t saved = hgatp_read();

    /* Write all-zero (MODE=Bare, VMID=0, PPN=0) */
    hgatp_write_raw(0UL);
    uintptr_t readback = hgatp_read();

    TEST_ASSERT_EQ("hgatp == 0 (all fields zero in Bare)", readback, 0UL);

    hgatp_write_raw(saved);
    HYP_TEST_END();
}

/* ---- HGATP-BARE-02 ---- */
TEST_REGISTER(test_shgatpa_bare_switch_back);
bool test_shgatpa_bare_switch_back(void) {
    TEST_BEGIN("HGATP-BARE-02: hgatp switches from SvNNx4 back to Bare");

    uintptr_t saved = hgatp_read();

    /* Set an SvNNx4 mode if available */
    if (g_satp_supports_sv39) {
        hgatp_write_raw(MAKE_HGATP(HGATP_MODE_SV39X4, 0, 0x1000));
        uintptr_t mid_mode = HGATP_GET_MODE(hgatp_read());
        TEST_ASSERT_EQ("hgatp in Sv39x4 mode before switch",
                       mid_mode, (uintptr_t)HGATP_MODE_SV39X4);
    }

    /* Switch back to Bare (all zero) */
    hgatp_write_raw(0UL);
    uintptr_t readback = hgatp_read();

    TEST_ASSERT_EQ("hgatp.MODE == Bare after switch",
                   HGATP_GET_MODE(readback), (uintptr_t)HGATP_MODE_BARE);
    TEST_ASSERT_EQ("hgatp == 0 (all fields zero in Bare)", readback, 0UL);

    hgatp_write_raw(saved);
    HYP_TEST_END();
}

/* ---- HGATP-BARE-03 ---- */
TEST_REGISTER(test_shgatpa_bare_ppn_vmid_zero);
bool test_shgatpa_bare_ppn_vmid_zero(void) {
    TEST_BEGIN("HGATP-BARE-03: hgatp Bare mode PPN/VMID are zero");

    uintptr_t saved = hgatp_read();

    /* Write Bare (all zero, per spec requirement) */
    hgatp_write_raw(0UL);
    uintptr_t readback = hgatp_read();

    TEST_ASSERT_EQ("hgatp.PPN == 0 in Bare mode",
                   HGATP_GET_PPN(readback), 0UL);
    TEST_ASSERT_EQ("hgatp.VMID == 0 in Bare mode",
                   HGATP_GET_VMID(readback), 0UL);

    hgatp_write_raw(saved);
    HYP_TEST_END();
}
