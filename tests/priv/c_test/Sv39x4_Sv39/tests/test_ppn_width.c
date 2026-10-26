/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * common/hyp/tests_2stage/test_group24_ppn_width.c
 *
 * Group 24: VS-stage PPN width (44-bit) verification
 *           (TS-PPNW-01..04)
 *
 * norm:satp_ppn_sv39_sz / norm:satp_ppn_sv48_sz / norm:satp_ppn_sv57_sz
 * state that Sv39/Sv48/Sv57 translate the VPN into a 44-bit PPN, so
 * a VS-stage (vsatp) leaf PTE must retain the full 44-bit PPN field
 * and VS-stage translation can output a GPA up to bit 55 (44 + 12).
 *
 * Under two-stage translation the GPA produced by VS-stage feeds the
 * G-stage. When the G-stage mode is wide enough (Sv48x4: 50-bit GPA
 * space, Sv57x4: 59-bit GPA space), a high GPA must translate
 * successfully instead of being truncated.
 *
 * Strategy: VS-stage maps the test VA to a high GPA that has no real
 * memory behind it; G-stage remaps that high GPA onto the real
 * low-address test_data_area page. A successful VS-mode R/W proves
 * the high VS-stage PPN bits were preserved end-to-end.
 *
 *   TS-PPNW-01  Sv39 + Sv48x4   GPA = 2^41 (PPN bit29, beyond the
 *                                Sv39x4 41-bit GPA boundary)
 *   TS-PPNW-02  Sv39 + Sv57x4   GPA = 2^55 (PPN bit43, top of the
 *                                44-bit PPN field)
 *   TS-PPNW-03  Sv48 + Sv57x4   GPA = 2^50 (PPN bit38)
 *   TS-PPNW-04  Sv57 + Sv57x4   GPA = 2^55 (PPN bit43)
 *
 * The negative counterpart (high GPA beyond a narrow G-stage must
 * raise guest-page-fault cause=21) is covered by Group 4
 * (TS-XMODE-19..21 in test_cross_width.c).
 * =================================================================== */

#include "two_stage_helpers.h"

/* Highest GPA bit reachable through a 44-bit VS-stage PPN:
 * PPN bit43 + 12-bit page offset = GPA bit55. */
#define VS_PPN_TOP_GPA_BIT  55

/* ----- Local helper (file-scope) ------------------------------- */

static bool g24_run_success(int vs_mode, int g_mode, int gpa_bit)
{
    two_stage_ctx_t ctx;
    gpt_pool_reset();
    pt_pool_reset();
    two_stage_init(&ctx, vs_mode, g_mode);

    /* Kernel/UART/trampoline pages on both stages */
    ts2_map_low_mem_both(&ctx);
    /* G-stage identity mapping of the test region (trampoline pages) */
    ts2_map_region_g(&ctx, PT_LEVEL_2M);

    uintptr_t va       = (uintptr_t)test_data_area;
    uintptr_t spa      = (uintptr_t)test_data_area;
    uintptr_t high_gpa = 1UL << gpa_bit;

    /* VS-stage: VA -> high GPA, exercising high PPN bits */
    int ret = pt_map_page(&ctx.vs_ctx, va, high_gpa,
                          VS_FLAGS_RWX_S_AD, PT_LEVEL_4K);
    if (ret != 0) {
        ts2_finish(&ctx);
        return false;
    }

    /* G-stage: high GPA -> real low-address SPA */
    ret = gpt_map_page(&ctx.g_ctx, high_gpa, spa,
                       G_FLAGS_RWXU_AD, PT_LEVEL_4K);
    if (ret != 0) {
        ts2_finish(&ctx);
        return false;
    }

    uintptr_t r = ts2_run_check_no_fault(&ctx, test_vs_read_write, va);
    bool ok = (r == 0);
    ts2_finish(&ctx);
    return ok;
}

/* ===================================================================
 * TS-PPNW-01: Sv39 VS-stage outputs GPA >= 2^41 (Sv48x4 G-stage)
 * =================================================================== */
TEST_REGISTER(test_ts_ppnw_01_sv39_sv48x4_gpa41);
bool test_ts_ppnw_01_sv39_sv48x4_gpa41(void)
{
    TEST_BEGIN("TS-PPNW-01: Sv39 VS-stage full-width PPN, GPA=2^41 + Sv48x4");
    REQUIRE_VSATP_MODE(SATP_MODE_SV39);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV48X4);
    bool ok = g24_run_success(SATP_MODE_SV39, HGATP_MODE_SV48X4,
                              SV39X4_GPA_BITS);
    TEST_ASSERT("R/W via VS-stage PPN bit29 under Sv48x4 "
                "[norm:satp_ppn_sv39_sz]", ok);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-PPNW-02: Sv39 VS-stage outputs GPA bit55 (Sv57x4 G-stage)
 * =================================================================== */
TEST_REGISTER(test_ts_ppnw_02_sv39_sv57x4_gpa55);
bool test_ts_ppnw_02_sv39_sv57x4_gpa55(void)
{
    TEST_BEGIN("TS-PPNW-02: Sv39 VS-stage top PPN bit, GPA=2^55 + Sv57x4");
    REQUIRE_VSATP_MODE(SATP_MODE_SV39);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV57X4);
    bool ok = g24_run_success(SATP_MODE_SV39, HGATP_MODE_SV57X4,
                              VS_PPN_TOP_GPA_BIT);
    TEST_ASSERT("R/W via VS-stage PPN bit43 under Sv57x4 "
                "[norm:satp_ppn_sv39_sz]", ok);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-PPNW-03: Sv48 VS-stage outputs GPA >= 2^50 (Sv57x4 G-stage)
 * =================================================================== */
TEST_REGISTER(test_ts_ppnw_03_sv48_sv57x4_gpa50);
bool test_ts_ppnw_03_sv48_sv57x4_gpa50(void)
{
    TEST_BEGIN("TS-PPNW-03: Sv48 VS-stage full-width PPN, GPA=2^50 + Sv57x4");
    REQUIRE_VSATP_MODE(SATP_MODE_SV48);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV57X4);
    bool ok = g24_run_success(SATP_MODE_SV48, HGATP_MODE_SV57X4,
                              SV48X4_GPA_BITS);
    TEST_ASSERT("R/W via VS-stage PPN bit38 under Sv57x4 "
                "[norm:satp_ppn_sv48_sz]", ok);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-PPNW-04: Sv57 VS-stage outputs GPA bit55 (Sv57x4 G-stage)
 * =================================================================== */
TEST_REGISTER(test_ts_ppnw_04_sv57_sv57x4_gpa55);
bool test_ts_ppnw_04_sv57_sv57x4_gpa55(void)
{
    TEST_BEGIN("TS-PPNW-04: Sv57 VS-stage top PPN bit, GPA=2^55 + Sv57x4");
    REQUIRE_VSATP_MODE(SATP_MODE_SV57);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV57X4);
    bool ok = g24_run_success(SATP_MODE_SV57, HGATP_MODE_SV57X4,
                              VS_PPN_TOP_GPA_BIT);
    TEST_ASSERT("R/W via VS-stage PPN bit43 under Sv57x4 "
                "[norm:satp_ppn_sv57_sz]", ok);
    HYP_TEST_END();
}
