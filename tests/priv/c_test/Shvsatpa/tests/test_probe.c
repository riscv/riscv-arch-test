/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 1: satp MODE support probing (baseline establishment)
 *
 * Spec anchors:
 *   norm:satp_mode         (supervisor.adoc:1009-1018)
 *   norm:satp_mode_sxlen64 (supervisor.adoc:1044-1050)
 *   norm:satp_mode_op_unsupported (supervisor.adoc:1052-1055)
 *
 * Test list (matches DOCS/testplan/shvsatpa_test_plan.md VSATP-PROBE):
 *   VSATP-PROBE-01  satp MODE=Bare probe
 *   VSATP-PROBE-02  satp MODE=Sv39 probe
 *   VSATP-PROBE-03  satp MODE=Sv48 probe
 *   VSATP-PROBE-04  satp MODE=Sv57 probe
 *
 * These tests probe satp for each standard MODE, recording results
 * into global booleans for Groups 2-5 to consume.
 *
 * Every probe goes through satp_probe_mode() (common/hyp/hyp_csr.c), which
 * runs the write/read-back/restore sequence inside one M-mode excursion.
 * satp translates the very mode that writes it, so probing a non-Bare MODE
 * directly from S(HS)-mode -- where the suite body runs under the T-SBI
 * S-mode-normal boot -- would switch translation on with PPN=0 and fault on
 * the next instruction fetch. M-mode fetches ignore satp, so the probe is
 * both safe there and unchanged in meaning.
 * =================================================================== */

/* Global state: which MODEs does satp support? */
volatile bool g_satp_supports_bare = false;
volatile bool g_satp_supports_sv39 = false;
volatile bool g_satp_supports_sv48 = false;
volatile bool g_satp_supports_sv57 = false;

/* ---- VSATP-PROBE-01 ---- */
TEST_REGISTER(test_shvsatpa_probe_bare);
bool test_shvsatpa_probe_bare(void) {
    TEST_BEGIN("VSATP-PROBE-01: probe satp MODE=Bare support");

    /* Write Bare (MODE=0, ASID=0, PPN=0) */
    uintptr_t mode = SATP_GET_MODE(satp_probe_mode(SATP_MODE_BARE));

    if (mode == SATP_MODE_BARE) {
        g_satp_supports_bare = true;
    }

    TEST_ASSERT_EQ("satp MODE readback is Bare (0)", mode,
                   (uintptr_t)SATP_MODE_BARE);

    HYP_TEST_END();
}

/* ---- VSATP-PROBE-02 ---- */
TEST_REGISTER(test_shvsatpa_probe_sv39);
bool test_shvsatpa_probe_sv39(void) {
    TEST_BEGIN("VSATP-PROBE-02: probe satp MODE=Sv39 support");

    /* Probe Sv39 from a Bare baseline */
    uintptr_t mode = SATP_GET_MODE(satp_probe_mode(SATP_MODE_SV39));

    if (mode == SATP_MODE_SV39) {
        g_satp_supports_sv39 = true;
        LOG_I("satp supports Sv39\n");
    } else {
        g_satp_supports_sv39 = false;
        LOG_I("satp does NOT support Sv39 (readback MODE=%lu)\n",
              (unsigned long)mode);
    }

    TEST_ASSERT("satp MODE readback is legal (0 or 8)",
                mode == SATP_MODE_BARE || mode == SATP_MODE_SV39);

    HYP_TEST_END();
}

/* ---- VSATP-PROBE-03 ---- */
TEST_REGISTER(test_shvsatpa_probe_sv48);
bool test_shvsatpa_probe_sv48(void) {
    TEST_BEGIN("VSATP-PROBE-03: probe satp MODE=Sv48 support");

    uintptr_t mode = SATP_GET_MODE(satp_probe_mode(SATP_MODE_SV48));

    if (mode == SATP_MODE_SV48) {
        g_satp_supports_sv48 = true;
        LOG_I("satp supports Sv48\n");
    } else {
        g_satp_supports_sv48 = false;
        LOG_I("satp does NOT support Sv48 (readback MODE=%lu)\n",
              (unsigned long)mode);
    }

    TEST_ASSERT("satp MODE readback is legal (0 or 9)",
                mode == SATP_MODE_BARE || mode == SATP_MODE_SV48);

    HYP_TEST_END();
}

/* ---- VSATP-PROBE-04 ---- */
TEST_REGISTER(test_shvsatpa_probe_sv57);
bool test_shvsatpa_probe_sv57(void) {
    TEST_BEGIN("VSATP-PROBE-04: probe satp MODE=Sv57 support");

    uintptr_t mode = SATP_GET_MODE(satp_probe_mode(SATP_MODE_SV57));

    if (mode == SATP_MODE_SV57) {
        g_satp_supports_sv57 = true;
        LOG_I("satp supports Sv57\n");
    } else {
        g_satp_supports_sv57 = false;
        LOG_I("satp does NOT support Sv57 (readback MODE=%lu)\n",
              (unsigned long)mode);
    }

    TEST_ASSERT("satp MODE readback is legal (0 or 10)",
                mode == SATP_MODE_BARE || mode == SATP_MODE_SV57);

    HYP_TEST_END();
}
