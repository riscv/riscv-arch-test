/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 6: ASID field width consistency
 *
 * Spec anchors:
 *   norm:vsatp_asid_op             (hypervisor.adoc:1394-1400)
 *   norm:shvsatpa_satp_vsatp_modes (shvsatpa.adoc:4-6)
 *
 * Test list (matches DOCS/testplan/shvsatpa_test_plan.md VSATP-ASID):
 *   VSATP-ASID-01  vsatp ASID width matches satp ASID width
 * =================================================================== */

/* ---- VSATP-ASID-01 ---- */
TEST_REGISTER(test_shvsatpa_asid_width);
bool test_shvsatpa_asid_width(void) {
    TEST_BEGIN("VSATP-ASID-01: vsatp ASID width matches satp ASID width");

    unsigned satp_bits  = satp_asid_width();
    unsigned vsatp_bits = vsatp_asid_width();

    LOG_I("satp ASID width = %u bits, vsatp ASID width = %u bits\n",
          satp_bits, vsatp_bits);

    TEST_ASSERT_EQ("vsatp ASID width == satp ASID width",
                   (uintptr_t)vsatp_bits, (uintptr_t)satp_bits);

    HYP_TEST_END();
}
