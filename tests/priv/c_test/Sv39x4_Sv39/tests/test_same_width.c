/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * common/hyp/tests_2stage/test_group03_same_width.c
 *
 * Group 3: Same-width 2-stage translation (TS-MAP-01..12)
 *
 * Verifies that VS-stage and G-stage cooperate correctly when both
 * stages use the *same* mode width:
 *   Sv39  + Sv39x4
 *   Sv48  + Sv48x4
 *   Sv57  + Sv57x4
 *
 * Each (vs_mode, g_mode) pair is exercised at matching leaf granularities:
 *   - 1GB / 1GB   (both stages use the largest common superpage)
 *   - 2MB / 2MB   (mid-size superpage)
 *   - 4KB / 4KB   (the "canonical" base page layout)
 *   - Mixed superpage (e.g. VS=1G + G=4K) to verify cross-granularity
 *   - 512GB / 512GB terapage (Sv48+ only)
 *   - VU-mode two-stage access (MAP-12)
 *
 * The success criterion is identical across all 12 cases: a VS-mode
 * read+write to test_data_area returns the magic value, indicating
 * both stages walked successfully.
 *
 * Helpers: builds the layouts manually rather than via
 * ts2_setup_full() because that helper hard-codes 4KB G-stage leafs.
 * =================================================================== */

#include "two_stage_helpers.h"

/* ----- Local helpers (file-scope, not registered) -------------- */

/* Run a same-width 2-stage R/W sanity check at given vs_level/g_level. */
static bool g3_run_one(int vs_mode, int g_mode, int vs_level, int g_level)
{
    two_stage_ctx_t ctx;
    ts2_setup_granular(&ctx, vs_mode, g_mode, vs_level, g_level);

    uintptr_t va = (uintptr_t)test_data_area;
    uintptr_t r  = ts2_run_check_no_fault(&ctx, test_vs_read_write, va);
    bool ok = (r == 0);
    ts2_finish(&ctx);
    return ok;
}

/* ===================================================================
 * Sv39 + Sv39x4 (TS-MAP-01..04)
 * =================================================================== */
TEST_REGISTER(test_ts_map_01_sv39_1g_1g);
bool test_ts_map_01_sv39_1g_1g(void)
{
    TEST_BEGIN("TS-MAP-01: Sv39+Sv39x4 VS=1G G=1G identity R/W");
    REQUIRE_VSATP_MODE(SATP_MODE_SV39);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV39X4);
    bool ok = g3_run_one(SATP_MODE_SV39, HGATP_MODE_SV39X4,
                         PT_LEVEL_1G, PT_LEVEL_1G);
    TEST_ASSERT("R/W under Sv39+Sv39x4 1G/1G", ok);
    HYP_TEST_END();
}

TEST_REGISTER(test_ts_map_02_sv39_2m_2m);
bool test_ts_map_02_sv39_2m_2m(void)
{
    TEST_BEGIN("TS-MAP-02: Sv39+Sv39x4 VS=2M G=2M");
    REQUIRE_VSATP_MODE(SATP_MODE_SV39);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV39X4);
    bool ok = g3_run_one(SATP_MODE_SV39, HGATP_MODE_SV39X4,
                         PT_LEVEL_2M, PT_LEVEL_2M);
    TEST_ASSERT("R/W under Sv39+Sv39x4 2M/2M", ok);
    HYP_TEST_END();
}

TEST_REGISTER(test_ts_map_03_sv39_4k_4k);
bool test_ts_map_03_sv39_4k_4k(void)
{
    TEST_BEGIN("TS-MAP-03: Sv39+Sv39x4 VS=4K G=4K");
    REQUIRE_VSATP_MODE(SATP_MODE_SV39);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV39X4);
    bool ok = g3_run_one(SATP_MODE_SV39, HGATP_MODE_SV39X4,
                         PT_LEVEL_4K, PT_LEVEL_4K);
    TEST_ASSERT("R/W under Sv39+Sv39x4 4K/4K", ok);
    HYP_TEST_END();
}

TEST_REGISTER(test_ts_map_04_sv39_1g_4k);
bool test_ts_map_04_sv39_1g_4k(void)
{
    TEST_BEGIN("TS-MAP-04: Sv39+Sv39x4 VS=1G G=4K (superpage mix)");
    REQUIRE_VSATP_MODE(SATP_MODE_SV39);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV39X4);
    bool ok = g3_run_one(SATP_MODE_SV39, HGATP_MODE_SV39X4,
                         PT_LEVEL_1G, PT_LEVEL_4K);
    TEST_ASSERT("R/W under Sv39+Sv39x4 1G/4K (superpage mix)", ok);
    HYP_TEST_END();
}

/* ===================================================================
 * Sv48 + Sv48x4 (TS-MAP-05..08)
 * =================================================================== */
TEST_REGISTER(test_ts_map_05_sv48_1g_1g);
bool test_ts_map_05_sv48_1g_1g(void)
{
    TEST_BEGIN("TS-MAP-05: Sv48+Sv48x4 VS=1G G=1G");
    REQUIRE_VSATP_MODE(SATP_MODE_SV48);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV48X4);
    bool ok = g3_run_one(SATP_MODE_SV48, HGATP_MODE_SV48X4,
                         PT_LEVEL_1G, PT_LEVEL_1G);
    TEST_ASSERT("R/W under Sv48+Sv48x4 1G/1G", ok);
    HYP_TEST_END();
}

TEST_REGISTER(test_ts_map_06_sv48_2m_2m);
bool test_ts_map_06_sv48_2m_2m(void)
{
    TEST_BEGIN("TS-MAP-06: Sv48+Sv48x4 VS=2M G=2M");
    REQUIRE_VSATP_MODE(SATP_MODE_SV48);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV48X4);
    bool ok = g3_run_one(SATP_MODE_SV48, HGATP_MODE_SV48X4,
                         PT_LEVEL_2M, PT_LEVEL_2M);
    TEST_ASSERT("R/W under Sv48+Sv48x4 2M/2M", ok);
    HYP_TEST_END();
}

TEST_REGISTER(test_ts_map_07_sv48_4k_4k);
bool test_ts_map_07_sv48_4k_4k(void)
{
    TEST_BEGIN("TS-MAP-07: Sv48+Sv48x4 VS=4K G=4K");
    REQUIRE_VSATP_MODE(SATP_MODE_SV48);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV48X4);
    bool ok = g3_run_one(SATP_MODE_SV48, HGATP_MODE_SV48X4,
                         PT_LEVEL_4K, PT_LEVEL_4K);
    TEST_ASSERT("R/W under Sv48+Sv48x4 4K/4K", ok);
    HYP_TEST_END();
}

TEST_REGISTER(test_ts_map_08_sv48_512g_512g);
bool test_ts_map_08_sv48_512g_512g(void)
{
    TEST_BEGIN("TS-MAP-08: Sv48+Sv48x4 VS=512G G=512G (terapage)");
    REQUIRE_VSATP_MODE(SATP_MODE_SV48);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV48X4);
    bool ok = g3_run_one(SATP_MODE_SV48, HGATP_MODE_SV48X4,
                         PT_LEVEL_512G, PT_LEVEL_512G);
    TEST_ASSERT("R/W under Sv48+Sv48x4 512G/512G", ok);
    HYP_TEST_END();
}

/* ===================================================================
 * Sv57 + Sv57x4 (TS-MAP-09..12)
 * =================================================================== */
TEST_REGISTER(test_ts_map_09_sv57_1g_1g);
bool test_ts_map_09_sv57_1g_1g(void)
{
    TEST_BEGIN("TS-MAP-09: Sv57+Sv57x4 VS=1G G=1G");
    REQUIRE_VSATP_MODE(SATP_MODE_SV57);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV57X4);
    bool ok = g3_run_one(SATP_MODE_SV57, HGATP_MODE_SV57X4,
                         PT_LEVEL_1G, PT_LEVEL_1G);
    TEST_ASSERT("R/W under Sv57+Sv57x4 1G/1G", ok);
    HYP_TEST_END();
}

TEST_REGISTER(test_ts_map_10_sv57_2m_2m);
bool test_ts_map_10_sv57_2m_2m(void)
{
    TEST_BEGIN("TS-MAP-10: Sv57+Sv57x4 VS=2M G=2M");
    REQUIRE_VSATP_MODE(SATP_MODE_SV57);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV57X4);
    bool ok = g3_run_one(SATP_MODE_SV57, HGATP_MODE_SV57X4,
                         PT_LEVEL_2M, PT_LEVEL_2M);
    TEST_ASSERT("R/W under Sv57+Sv57x4 2M/2M", ok);
    HYP_TEST_END();
}

TEST_REGISTER(test_ts_map_11_sv57_4k_4k);
bool test_ts_map_11_sv57_4k_4k(void)
{
    TEST_BEGIN("TS-MAP-11: Sv57+Sv57x4 VS=4K G=4K");
    REQUIRE_VSATP_MODE(SATP_MODE_SV57);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV57X4);
    bool ok = g3_run_one(SATP_MODE_SV57, HGATP_MODE_SV57X4,
                         PT_LEVEL_4K, PT_LEVEL_4K);
    TEST_ASSERT("R/W under Sv57+Sv57x4 4K/4K", ok);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-MAP-12: VU-mode two-stage access.
 *
 * Spec (norm:H_vm_gpapriv): For G-stage address translation, all
 * memory accesses are considered to be user-level accesses.
 * VU-mode is U-level in VS-stage: VS-stage PTE must have U=1,
 * G-stage PTE must also have U=1.
 * =================================================================== */
TEST_REGISTER(test_ts_map_12_vu_mode);
bool test_ts_map_12_vu_mode(void)
{
    TEST_BEGIN("TS-MAP-12: VU-mode two-stage access");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    /* Setup with U=1 in both VS-stage and G-stage for VU-mode. */
    ts2_setup_full_u(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    uintptr_t va = (uintptr_t)test_data_area;

    /* Keep any fault at HS rather than the standing VS entry:
     * ts2_setup_full_u maps all kernel text with U=1 for the VU
     * payload, and an S-level VS handler can never fetch from U=1
     * pages, so a delegated fault would re-fault the handler's own
     * fetch forever (hang) instead of failing this no-fault
     * assertion cleanly. No behavioural change while no fault
     * fires; HYP_TEST_END restores the delegation baseline. */
    setup_deleg_to_hs((1UL << CAUSE_LOAD_PAGE_FAULT) |
                      (1UL << CAUSE_STORE_PAGE_FAULT));

    trap_expect_begin();
    (void)two_stage_run_in_vu(&ctx, test_vs_read_write, va);
    bool fired = trap_was_triggered();
    trap_expect_end();
    ts2_finish(&ctx);

    TEST_ASSERT("VU-mode two-stage R/W succeeds (no fault)", !fired);
    HYP_TEST_END();
}
