/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * common/hyp/tests_2stage/test_group04_cross_width.c
 *
 * Group 4: Cross-width VS-stage <-> G-stage combinations
 *          (TS-XMODE-01..09 VS≤G, plus VS>G normal and fault)
 *
 * RISC-V Hypervisor architecture allows the VS-stage mode (vsatp) and
 * the G-stage mode (hgatp) to differ in width, subject to the rule
 * that VS-stage must not be wider than G-stage. Concretely, the
 * permitted combinations on a Sv57x4-capable platform are:
 *
 *   VS\G    Sv39x4   Sv48x4   Sv57x4
 *   ------  -------  -------  --------
 *   Sv39    n/a      ok       ok
 *   Sv48    VS>G     n/a      ok
 *   Sv57    VS>G     VS>G     n/a
 *
 * The "same" diagonal is exercised by Group 3. Group 4 covers:
 *   Part A - VS≤G (3 pairs × 3 G-levels = 9 tests):
 *     TS-XMODE-01..03  Sv39 + Sv48x4
 *     TS-XMODE-04..06  Sv39 + Sv57x4
 *     TS-XMODE-07..09  Sv48 + Sv57x4
 *
 *   Part B - VS>G Normal (GPA in range, 3 pairs × 3 G-levels = 9):
 *     TS-XMODE-10..12  Sv48 + Sv39x4  (GPA < 2^41)
 *     TS-XMODE-13..15  Sv57 + Sv39x4  (GPA < 2^41)
 *     TS-XMODE-16..18  Sv57 + Sv48x4  (GPA < 2^50)
 *
 *   Part C - VS>G Fault (GPA out of range, 3 tests):
 *     TS-XMODE-19  Sv48 + Sv39x4 GPA≥2^41 → cause=21
 *     TS-XMODE-20  Sv57 + Sv39x4 GPA≥2^41 → cause=21
 *     TS-XMODE-21  Sv57 + Sv48x4 GPA≥2^50 → cause=21
 * =================================================================== */

#include "two_stage_helpers.h"

/* ----- Local helpers (file-scope) ------------------------------ */

static bool g4_run_one(int vs_mode, int g_mode, int g_level)
{
    two_stage_ctx_t ctx;
    gpt_pool_reset();
    pt_pool_reset();
    two_stage_init(&ctx, vs_mode, g_mode);

    ts2_map_low_mem_both(&ctx);
    ts2_map_region_g(&ctx, g_level);
    ts2_map_region_vs(&ctx, PT_LEVEL_4K);

    uintptr_t va = (uintptr_t)test_data_area;
    uintptr_t r = ts2_run_check_no_fault(&ctx, test_vs_read_write, va);
    bool ok = (r == 0);
    ts2_finish(&ctx);
    return ok;
}

/* ===================================================================
 * Sv39 + Sv48x4  (TS-XMODE-01..03)
 * =================================================================== */
TEST_REGISTER(test_ts_xmode_01_sv39_sv48x4_4k);
bool test_ts_xmode_01_sv39_sv48x4_4k(void)
{
    TEST_BEGIN("TS-XMODE-01: Sv39+Sv48x4 4K/4K");
    REQUIRE_VSATP_MODE(SATP_MODE_SV39);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV48X4);
    bool ok = g4_run_one(SATP_MODE_SV39, HGATP_MODE_SV48X4, PT_LEVEL_4K);
    TEST_ASSERT("R/W under Sv39 + Sv48x4 (4K/4K)", ok);
    HYP_TEST_END();
}

TEST_REGISTER(test_ts_xmode_02_sv39_sv48x4_2m);
bool test_ts_xmode_02_sv39_sv48x4_2m(void)
{
    TEST_BEGIN("TS-XMODE-02: Sv39+Sv48x4 VS=4K G=2M");
    REQUIRE_VSATP_MODE(SATP_MODE_SV39);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV48X4);
    bool ok = g4_run_one(SATP_MODE_SV39, HGATP_MODE_SV48X4, PT_LEVEL_2M);
    TEST_ASSERT("R/W under Sv39 + Sv48x4 (4K/2M)", ok);
    HYP_TEST_END();
}

TEST_REGISTER(test_ts_xmode_03_sv39_sv48x4_1g);
bool test_ts_xmode_03_sv39_sv48x4_1g(void)
{
    TEST_BEGIN("TS-XMODE-03: Sv39+Sv48x4 VS=4K G=1G");
    REQUIRE_VSATP_MODE(SATP_MODE_SV39);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV48X4);
    bool ok = g4_run_one(SATP_MODE_SV39, HGATP_MODE_SV48X4, PT_LEVEL_1G);
    TEST_ASSERT("R/W under Sv39 + Sv48x4 (4K/1G)", ok);
    HYP_TEST_END();
}

/* ===================================================================
 * Sv39 + Sv57x4  (TS-XMODE-04..06)
 * =================================================================== */
TEST_REGISTER(test_ts_xmode_04_sv39_sv57x4_4k);
bool test_ts_xmode_04_sv39_sv57x4_4k(void)
{
    TEST_BEGIN("TS-XMODE-04: Sv39+Sv57x4 4K/4K");
    REQUIRE_VSATP_MODE(SATP_MODE_SV39);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV57X4);
    bool ok = g4_run_one(SATP_MODE_SV39, HGATP_MODE_SV57X4, PT_LEVEL_4K);
    TEST_ASSERT("R/W under Sv39 + Sv57x4 (4K/4K)", ok);
    HYP_TEST_END();
}

TEST_REGISTER(test_ts_xmode_05_sv39_sv57x4_2m);
bool test_ts_xmode_05_sv39_sv57x4_2m(void)
{
    TEST_BEGIN("TS-XMODE-05: Sv39+Sv57x4 VS=4K G=2M");
    REQUIRE_VSATP_MODE(SATP_MODE_SV39);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV57X4);
    bool ok = g4_run_one(SATP_MODE_SV39, HGATP_MODE_SV57X4, PT_LEVEL_2M);
    TEST_ASSERT("R/W under Sv39 + Sv57x4 (4K/2M)", ok);
    HYP_TEST_END();
}

TEST_REGISTER(test_ts_xmode_06_sv39_sv57x4_1g);
bool test_ts_xmode_06_sv39_sv57x4_1g(void)
{
    TEST_BEGIN("TS-XMODE-06: Sv39+Sv57x4 VS=4K G=1G");
    REQUIRE_VSATP_MODE(SATP_MODE_SV39);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV57X4);
    bool ok = g4_run_one(SATP_MODE_SV39, HGATP_MODE_SV57X4, PT_LEVEL_1G);
    TEST_ASSERT("R/W under Sv39 + Sv57x4 (4K/1G)", ok);
    HYP_TEST_END();
}

/* ===================================================================
 * Sv48 + Sv57x4  (TS-XMODE-07..09)
 * =================================================================== */
TEST_REGISTER(test_ts_xmode_07_sv48_sv57x4_4k);
bool test_ts_xmode_07_sv48_sv57x4_4k(void)
{
    TEST_BEGIN("TS-XMODE-07: Sv48+Sv57x4 4K/4K");
    REQUIRE_VSATP_MODE(SATP_MODE_SV48);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV57X4);
    bool ok = g4_run_one(SATP_MODE_SV48, HGATP_MODE_SV57X4, PT_LEVEL_4K);
    TEST_ASSERT("R/W under Sv48 + Sv57x4 (4K/4K)", ok);
    HYP_TEST_END();
}

TEST_REGISTER(test_ts_xmode_08_sv48_sv57x4_2m);
bool test_ts_xmode_08_sv48_sv57x4_2m(void)
{
    TEST_BEGIN("TS-XMODE-08: Sv48+Sv57x4 VS=4K G=2M");
    REQUIRE_VSATP_MODE(SATP_MODE_SV48);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV57X4);
    bool ok = g4_run_one(SATP_MODE_SV48, HGATP_MODE_SV57X4, PT_LEVEL_2M);
    TEST_ASSERT("R/W under Sv48 + Sv57x4 (4K/2M)", ok);
    HYP_TEST_END();
}

TEST_REGISTER(test_ts_xmode_09_sv48_sv57x4_1g);
bool test_ts_xmode_09_sv48_sv57x4_1g(void)
{
    TEST_BEGIN("TS-XMODE-09: Sv48+Sv57x4 VS=4K G=1G");
    REQUIRE_VSATP_MODE(SATP_MODE_SV48);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV57X4);
    bool ok = g4_run_one(SATP_MODE_SV48, HGATP_MODE_SV57X4, PT_LEVEL_1G);
    TEST_ASSERT("R/W under Sv48 + Sv57x4 (4K/1G)", ok);
    HYP_TEST_END();
}

/* ===================================================================
 * Part B: VS>G Normal flow (GPA within G-stage addressable range)
 *
 * When VS-stage is wider than G-stage (e.g. Sv48 + Sv39x4), the
 * combination still works correctly as long as the GPA produced by
 * VS-stage translation falls within the G-stage addressable range.
 * Since test_data_area resides in low memory (< 4GB), identity
 * mapping guarantees GPA is well within range.
 * =================================================================== */

/* ===================================================================
 * Sv48 + Sv39x4  (TS-XMODE-10..12)  GPA < 2^41
 * =================================================================== */
TEST_REGISTER(test_ts_xmode_10_sv48_sv39x4_4k);
bool test_ts_xmode_10_sv48_sv39x4_4k(void)
{
    TEST_BEGIN("TS-XMODE-10: Sv48+Sv39x4 VS=4K G=4K (VS>G normal)");
    REQUIRE_VSATP_MODE(SATP_MODE_SV48);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV39X4);
    bool ok = g4_run_one(SATP_MODE_SV48, HGATP_MODE_SV39X4, PT_LEVEL_4K);
    TEST_ASSERT("R/W under Sv48 + Sv39x4 (4K/4K)", ok);
    HYP_TEST_END();
}

TEST_REGISTER(test_ts_xmode_11_sv48_sv39x4_2m);
bool test_ts_xmode_11_sv48_sv39x4_2m(void)
{
    TEST_BEGIN("TS-XMODE-11: Sv48+Sv39x4 VS=4K G=2M (VS>G normal)");
    REQUIRE_VSATP_MODE(SATP_MODE_SV48);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV39X4);
    bool ok = g4_run_one(SATP_MODE_SV48, HGATP_MODE_SV39X4, PT_LEVEL_2M);
    TEST_ASSERT("R/W under Sv48 + Sv39x4 (4K/2M)", ok);
    HYP_TEST_END();
}

TEST_REGISTER(test_ts_xmode_12_sv48_sv39x4_1g);
bool test_ts_xmode_12_sv48_sv39x4_1g(void)
{
    TEST_BEGIN("TS-XMODE-12: Sv48+Sv39x4 VS=4K G=1G (VS>G normal)");
    REQUIRE_VSATP_MODE(SATP_MODE_SV48);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV39X4);
    bool ok = g4_run_one(SATP_MODE_SV48, HGATP_MODE_SV39X4, PT_LEVEL_1G);
    TEST_ASSERT("R/W under Sv48 + Sv39x4 (4K/1G)", ok);
    HYP_TEST_END();
}

/* ===================================================================
 * Sv57 + Sv39x4  (TS-XMODE-13..15)  GPA < 2^41
 * =================================================================== */
TEST_REGISTER(test_ts_xmode_13_sv57_sv39x4_4k);
bool test_ts_xmode_13_sv57_sv39x4_4k(void)
{
    TEST_BEGIN("TS-XMODE-13: Sv57+Sv39x4 VS=4K G=4K (VS>G normal)");
    REQUIRE_VSATP_MODE(SATP_MODE_SV57);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV39X4);
    bool ok = g4_run_one(SATP_MODE_SV57, HGATP_MODE_SV39X4, PT_LEVEL_4K);
    TEST_ASSERT("R/W under Sv57 + Sv39x4 (4K/4K)", ok);
    HYP_TEST_END();
}

TEST_REGISTER(test_ts_xmode_14_sv57_sv39x4_2m);
bool test_ts_xmode_14_sv57_sv39x4_2m(void)
{
    TEST_BEGIN("TS-XMODE-14: Sv57+Sv39x4 VS=4K G=2M (VS>G normal)");
    REQUIRE_VSATP_MODE(SATP_MODE_SV57);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV39X4);
    bool ok = g4_run_one(SATP_MODE_SV57, HGATP_MODE_SV39X4, PT_LEVEL_2M);
    TEST_ASSERT("R/W under Sv57 + Sv39x4 (4K/2M)", ok);
    HYP_TEST_END();
}

TEST_REGISTER(test_ts_xmode_15_sv57_sv39x4_1g);
bool test_ts_xmode_15_sv57_sv39x4_1g(void)
{
    TEST_BEGIN("TS-XMODE-15: Sv57+Sv39x4 VS=4K G=1G (VS>G normal)");
    REQUIRE_VSATP_MODE(SATP_MODE_SV57);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV39X4);
    bool ok = g4_run_one(SATP_MODE_SV57, HGATP_MODE_SV39X4, PT_LEVEL_1G);
    TEST_ASSERT("R/W under Sv57 + Sv39x4 (4K/1G)", ok);
    HYP_TEST_END();
}

/* ===================================================================
 * Sv57 + Sv48x4  (TS-XMODE-16..18)  GPA < 2^50
 * =================================================================== */
TEST_REGISTER(test_ts_xmode_16_sv57_sv48x4_4k);
bool test_ts_xmode_16_sv57_sv48x4_4k(void)
{
    TEST_BEGIN("TS-XMODE-16: Sv57+Sv48x4 VS=4K G=4K (VS>G normal)");
    REQUIRE_VSATP_MODE(SATP_MODE_SV57);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV48X4);
    bool ok = g4_run_one(SATP_MODE_SV57, HGATP_MODE_SV48X4, PT_LEVEL_4K);
    TEST_ASSERT("R/W under Sv57 + Sv48x4 (4K/4K)", ok);
    HYP_TEST_END();
}

TEST_REGISTER(test_ts_xmode_17_sv57_sv48x4_2m);
bool test_ts_xmode_17_sv57_sv48x4_2m(void)
{
    TEST_BEGIN("TS-XMODE-17: Sv57+Sv48x4 VS=4K G=2M (VS>G normal)");
    REQUIRE_VSATP_MODE(SATP_MODE_SV57);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV48X4);
    bool ok = g4_run_one(SATP_MODE_SV57, HGATP_MODE_SV48X4, PT_LEVEL_2M);
    TEST_ASSERT("R/W under Sv57 + Sv48x4 (4K/2M)", ok);
    HYP_TEST_END();
}

TEST_REGISTER(test_ts_xmode_18_sv57_sv48x4_1g);
bool test_ts_xmode_18_sv57_sv48x4_1g(void)
{
    TEST_BEGIN("TS-XMODE-18: Sv57+Sv48x4 VS=4K G=1G (VS>G normal)");
    REQUIRE_VSATP_MODE(SATP_MODE_SV57);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV48X4);
    bool ok = g4_run_one(SATP_MODE_SV57, HGATP_MODE_SV48X4, PT_LEVEL_1G);
    TEST_ASSERT("R/W under Sv57 + Sv48x4 (4K/1G)", ok);
    HYP_TEST_END();
}

/* ===================================================================
 * Part C: VS>G Fault flow (GPA exceeds G-stage addressable range)
 *
 * When VS-stage translation produces a GPA that exceeds the G-stage
 * addressable range (e.g. GPA >= 2^41 under Sv39x4), the hardware
 * must raise a guest-page-fault (cause=21 for load).
 *
 * Implementation: Tamper with the VS leaf PTE's PPN to point beyond
 * the G-stage GPA limit. The test_data_area VA is mapped in VS-stage
 * to an out-of-range GPA, triggering the fault.
 * =================================================================== */

static bool g4_run_fault(int vs_mode, int g_mode, int gpa_bits)
{
    two_stage_ctx_t ctx;
    gpt_pool_reset();
    pt_pool_reset();
    two_stage_init(&ctx, vs_mode, g_mode);

    /* Map low memory normally so trampoline can execute */
    ts2_map_low_mem_both(&ctx);

    /* Map test region at G-stage with 2M (needed for trampoline pages) */
    ts2_map_region_g(&ctx, PT_LEVEL_2M);

    /* VS-stage: map test_data_area to an out-of-range GPA.
     * The OOB GPA is the first address beyond the G-stage limit. */
    uintptr_t va = (uintptr_t)test_data_area;
    uintptr_t oob_gpa = 1UL << gpa_bits;
    (void)pt_map_page(&ctx.vs_ctx, va, oob_gpa,
                      VS_FLAGS_RWX_S_AD, PT_LEVEL_4K);

    bool ok = ts2_run_check_fault(&ctx, test_vs_load_expect_fault, va,
                                  CAUSE_LOAD_GUEST_PAGE_FAULT);
    return ok;
}

/* ===================================================================
 * TS-XMODE-19: Sv48 + Sv39x4 GPA ≥ 2^41
 * =================================================================== */
TEST_REGISTER(test_ts_xmode_19_sv48_sv39x4_fault);
bool test_ts_xmode_19_sv48_sv39x4_fault(void)
{
    TEST_BEGIN("TS-XMODE-19: Sv48+Sv39x4 GPA out-of-range -> cause=21");
    REQUIRE_VSATP_MODE(SATP_MODE_SV48);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV39X4);
    bool ok = g4_run_fault(SATP_MODE_SV48, HGATP_MODE_SV39X4,
                           SV39X4_GPA_BITS);
    TEST_ASSERT("cause = load-guest-page-fault (21) [GPA >= 2^41]", ok);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-XMODE-20: Sv57 + Sv39x4 GPA ≥ 2^41
 * =================================================================== */
TEST_REGISTER(test_ts_xmode_20_sv57_sv39x4_fault);
bool test_ts_xmode_20_sv57_sv39x4_fault(void)
{
    TEST_BEGIN("TS-XMODE-20: Sv57+Sv39x4 GPA out-of-range -> cause=21");
    REQUIRE_VSATP_MODE(SATP_MODE_SV57);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV39X4);
    bool ok = g4_run_fault(SATP_MODE_SV57, HGATP_MODE_SV39X4,
                           SV39X4_GPA_BITS);
    TEST_ASSERT("cause = load-guest-page-fault (21) [GPA >= 2^41]", ok);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-XMODE-21: Sv57 + Sv48x4 GPA ≥ 2^50
 * =================================================================== */
TEST_REGISTER(test_ts_xmode_21_sv57_sv48x4_fault);
bool test_ts_xmode_21_sv57_sv48x4_fault(void)
{
    TEST_BEGIN("TS-XMODE-21: Sv57+Sv48x4 GPA out-of-range -> cause=21");
    REQUIRE_VSATP_MODE(SATP_MODE_SV57);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV48X4);
    bool ok = g4_run_fault(SATP_MODE_SV57, HGATP_MODE_SV48X4,
                           SV48X4_GPA_BITS);
    TEST_ASSERT("cause = load-guest-page-fault (21) [GPA >= 2^50]", ok);
    HYP_TEST_END();
}
