/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 2: vsatp MODE consistency with satp (V=0 direct access)
 *
 * Spec anchors:
 *   norm:shvsatpa_satp_vsatp_modes (shvsatpa.adoc:4-6)
 *   norm:vsatp_sz_acc_op           (hypervisor.adoc:1384-1392)
 *
 * Test list (matches DOCS/testplan/shvsatpa_test_plan.md VSATP-MODE):
 *   VSATP-MODE-01  vsatp MODE=Bare support
 *   VSATP-MODE-02  vsatp MODE=Sv39 support (if satp supports)
 *   VSATP-MODE-03  vsatp MODE=Sv48 support (if satp supports)
 *   VSATP-MODE-04  vsatp MODE=Sv57 support (if satp supports)
 *
 * Core Shvsatpa validation: for each MODE that satp supports,
 * writing it to vsatp (CSR 0x280) must succeed.
 * =================================================================== */

extern volatile bool g_satp_supports_bare;
extern volatile bool g_satp_supports_sv39;
extern volatile bool g_satp_supports_sv48;
extern volatile bool g_satp_supports_sv57;

/* ---- VSATP-MODE-01 ---- */
TEST_REGISTER(test_shvsatpa_vsatp_mode_bare);
bool test_shvsatpa_vsatp_mode_bare(void) {
    TEST_BEGIN("VSATP-MODE-01: vsatp supports MODE=Bare");

    uintptr_t saved = vsatp_read();

    vsatp_write(MAKE_SATP(SATP_MODE_BARE, 0, 0));
    uintptr_t mode = SATP_GET_MODE(vsatp_read());

    TEST_ASSERT_EQ("vsatp.MODE == Bare (0)", mode,
                   (uintptr_t)SATP_MODE_BARE);

    vsatp_write(saved);
    HYP_TEST_END();
}

/* ---- VSATP-MODE-02 ---- */
TEST_REGISTER(test_shvsatpa_vsatp_mode_sv39);
bool test_shvsatpa_vsatp_mode_sv39(void) {
    TEST_BEGIN("VSATP-MODE-02: vsatp supports Sv39 if satp does");

    if (!g_satp_supports_sv39) {
        TEST_SKIP("satp does not support Sv39");
    }

    uintptr_t saved = vsatp_read();

    vsatp_write(MAKE_SATP(SATP_MODE_BARE, 0, 0));
    vsatp_write(MAKE_SATP(SATP_MODE_SV39, 0, 0));
    uintptr_t mode = SATP_GET_MODE(vsatp_read());

    TEST_ASSERT_EQ("vsatp.MODE == Sv39 (Shvsatpa requirement)",
                   mode, (uintptr_t)SATP_MODE_SV39);

    vsatp_write(saved);
    HYP_TEST_END();
}

/* ---- VSATP-MODE-03 ---- */
TEST_REGISTER(test_shvsatpa_vsatp_mode_sv48);
bool test_shvsatpa_vsatp_mode_sv48(void) {
    TEST_BEGIN("VSATP-MODE-03: vsatp supports Sv48 if satp does");

    if (!g_satp_supports_sv48) {
        TEST_SKIP("satp does not support Sv48");
    }

    uintptr_t saved = vsatp_read();

    vsatp_write(MAKE_SATP(SATP_MODE_BARE, 0, 0));
    vsatp_write(MAKE_SATP(SATP_MODE_SV48, 0, 0));
    uintptr_t mode = SATP_GET_MODE(vsatp_read());

    TEST_ASSERT_EQ("vsatp.MODE == Sv48 (Shvsatpa requirement)",
                   mode, (uintptr_t)SATP_MODE_SV48);

    vsatp_write(saved);
    HYP_TEST_END();
}

/* ---- VSATP-MODE-04 ---- */
TEST_REGISTER(test_shvsatpa_vsatp_mode_sv57);
bool test_shvsatpa_vsatp_mode_sv57(void) {
    TEST_BEGIN("VSATP-MODE-04: vsatp supports Sv57 if satp does");

    if (!g_satp_supports_sv57) {
        TEST_SKIP("satp does not support Sv57");
    }

    uintptr_t saved = vsatp_read();

    vsatp_write(MAKE_SATP(SATP_MODE_BARE, 0, 0));
    vsatp_write(MAKE_SATP(SATP_MODE_SV57, 0, 0));
    uintptr_t mode = SATP_GET_MODE(vsatp_read());

    TEST_ASSERT_EQ("vsatp.MODE == Sv57 (Shvsatpa requirement)",
                   mode, (uintptr_t)SATP_MODE_SV57);

    vsatp_write(saved);
    HYP_TEST_END();
}
