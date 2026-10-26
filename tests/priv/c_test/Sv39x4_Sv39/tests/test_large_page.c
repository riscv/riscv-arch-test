/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * common/hyp/tests_2stage/test_group23_large_page.c
 *
 * Group 23: Large page-size two-stage combinations (TS-LP-01..10)
 *
 * Verifies that both VS-stage and G-stage correctly handle superpage
 * mappings beyond the common 4K/2M/1G sizes. Specifically:
 *
 *   - G-stage 512GB superpage (Sv48x4+, PT_LEVEL_512G)
 *   - G-stage 256TB superpage (Sv57x4 only, PT_LEVEL_256T)
 *   - VS-stage 1GB superpage (all modes Sv39+)
 *   - VS-stage 512GB superpage (Sv48+, PT_LEVEL_512G)
 *   - VS-stage 256TB superpage (Sv57 only, PT_LEVEL_256T)
 *
 * For G-stage large superpages, we map GPA=0 → SPA=0 at the large
 * level, which covers [0, 512G) or [0, 256T) — all platform memory
 * (both QEMU MEM_BASE=0x80000000 and HAPS MEM_BASE=0x60000000) falls
 * within this range.
 *
 * For VS-stage large superpages, we map VA=0 → GPA=0 at the large
 * level, creating a superpage leaf in the root (or near-root) PT page.
 * =================================================================== */

#include "two_stage_helpers.h"

/* ----- Local helpers ---------------------------------------------- */

/*
 * Run a test with VS-stage at vs_level and G-stage at g_level.
 * For G-stage large pages (512G/256T), a single superpage aligned to the
 * test region covers kernel + test region (plus a separate UART page).
 * For VS-stage large pages (1G/512G/256T), a single superpage maps from the
 * superpage-aligned test region base.
 */
static bool g23_run_one(int vs_mode, int g_mode, int vs_level, int g_level)
{
    two_stage_ctx_t ctx;
    gpt_pool_reset();
    pt_pool_reset();
    two_stage_init(&ctx, vs_mode, g_mode);

    /* G-stage mapping */
    if (g_level >= PT_LEVEL_512G) {
        /* Single region-aligned superpage covers kernel + test region
         * (and UART); no separate low-mem walk needed. */
        ts2_map_region_g(&ctx, g_level);
    } else if (g_level == PT_LEVEL_1G) {
        /* 1G superpages: cover test region, low memory, and UART */
        uintptr_t base1g = TEST_REGION_BASE & ~(PAGE_SIZE_1G - 1);
        (void)gpt_map_page(&ctx.g_ctx, base1g, base1g,
                           G_FLAGS_RWXU_AD, PT_LEVEL_1G);
        uintptr_t lo_1g = PLATFORM_MEM_BASE & ~(PAGE_SIZE_1G - 1);
        if (lo_1g != base1g) {
            (void)gpt_map_page(&ctx.g_ctx, lo_1g, lo_1g,
                               G_FLAGS_RWXU_AD, PT_LEVEL_1G);
        }
        uintptr_t uart_1g = PLATFORM_UART0_BASE & ~(PAGE_SIZE_1G - 1);
        if (uart_1g != base1g && uart_1g != lo_1g) {
            (void)gpt_map_page(&ctx.g_ctx, uart_1g, uart_1g,
                               G_FLAGS_RWXU_AD, PT_LEVEL_1G);
        }
    } else {
        /* Standard 4K/2M G-stage for test region + low memory */
        ts2_map_low_mem_g(&ctx);
        ts2_map_region_g(&ctx, g_level);
    }

    /* VS-stage mapping */
    if (vs_level >= PT_LEVEL_512G) {
        /* Single region-aligned superpage covers kernel + test region
         * (and UART); no separate low-mem walk needed. */
        ts2_map_region_vs(&ctx, vs_level);
    } else if (vs_level == PT_LEVEL_1G) {
        /* 1G superpages: cover test region, low memory, and UART */
        uintptr_t base1g = TEST_REGION_BASE & ~(PAGE_SIZE_1G - 1);
        (void)pt_map_page(&ctx.vs_ctx, base1g, base1g,
                          VS_FLAGS_RWX_S_AD, PT_LEVEL_1G);
        uintptr_t lo_1g = PLATFORM_MEM_BASE & ~(PAGE_SIZE_1G - 1);
        if (lo_1g != base1g) {
            (void)pt_map_page(&ctx.vs_ctx, lo_1g, lo_1g,
                              VS_FLAGS_RWX_S_AD, PT_LEVEL_1G);
        }
        uintptr_t uart_1g = PLATFORM_UART0_BASE & ~(PAGE_SIZE_1G - 1);
        if (uart_1g != base1g && uart_1g != lo_1g) {
            (void)pt_map_page(&ctx.vs_ctx, uart_1g, uart_1g,
                              VS_FLAGS_RWX_S_AD, PT_LEVEL_1G);
        }
    } else {
        /* Standard 4K/2M VS-stage */
        ts2_map_low_mem_vs(&ctx);
        ts2_map_region_vs(&ctx, vs_level);
    }

    uintptr_t va = (uintptr_t)test_data_area;
    uintptr_t r = ts2_run_check_no_fault(&ctx, test_vs_read_write, va);
    bool ok = (r == 0);
    ts2_finish(&ctx);
    return ok;
}

/* ===================================================================
 * TS-LP-01..03: VS=1G superpage, G-stage at 4K/2M/1G
 * Requires: Sv39+ (all modes support 1G leaf at level 2)
 * =================================================================== */
TEST_REGISTER(test_ts_lp_01_vs1g_g4k);
bool test_ts_lp_01_vs1g_g4k(void)
{
    TEST_BEGIN("TS-LP-01: VS=1G G=4K");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);
    bool ok = g23_run_one(SUITE_VSATP_MODE, SUITE_HGATP_MODE,
                          PT_LEVEL_1G, PT_LEVEL_4K);
    TEST_ASSERT("R/W under VS=1G + G=4K", ok);
    HYP_TEST_END();
}

TEST_REGISTER(test_ts_lp_02_vs1g_g2m);
bool test_ts_lp_02_vs1g_g2m(void)
{
    TEST_BEGIN("TS-LP-02: VS=1G G=2M");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);
    bool ok = g23_run_one(SUITE_VSATP_MODE, SUITE_HGATP_MODE,
                          PT_LEVEL_1G, PT_LEVEL_2M);
    TEST_ASSERT("R/W under VS=1G + G=2M", ok);
    HYP_TEST_END();
}

TEST_REGISTER(test_ts_lp_03_vs1g_g1g);
bool test_ts_lp_03_vs1g_g1g(void)
{
    TEST_BEGIN("TS-LP-03: VS=1G G=1G");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);
    bool ok = g23_run_one(SUITE_VSATP_MODE, SUITE_HGATP_MODE,
                          PT_LEVEL_1G, PT_LEVEL_1G);
    TEST_ASSERT("R/W under VS=1G + G=1G", ok);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-LP-04..06: G=512G superpage, VS at 4K/2M/1G
 * Requires: Sv48x4+ (512G leaf at level 3 needs 4+ levels)
 * =================================================================== */
TEST_REGISTER(test_ts_lp_04_vs4k_g512g);
bool test_ts_lp_04_vs4k_g512g(void)
{
    TEST_BEGIN("TS-LP-04: VS=4K G=512G");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV48X4);
    bool ok = g23_run_one(SUITE_VSATP_MODE, HGATP_MODE_SV48X4,
                          PT_LEVEL_4K, PT_LEVEL_512G);
    TEST_ASSERT("R/W under VS=4K + G=512G", ok);
    HYP_TEST_END();
}

TEST_REGISTER(test_ts_lp_05_vs2m_g512g);
bool test_ts_lp_05_vs2m_g512g(void)
{
    TEST_BEGIN("TS-LP-05: VS=2M G=512G");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV48X4);
    bool ok = g23_run_one(SUITE_VSATP_MODE, HGATP_MODE_SV48X4,
                          PT_LEVEL_2M, PT_LEVEL_512G);
    TEST_ASSERT("R/W under VS=2M + G=512G", ok);
    HYP_TEST_END();
}

TEST_REGISTER(test_ts_lp_06_vs1g_g512g);
bool test_ts_lp_06_vs1g_g512g(void)
{
    TEST_BEGIN("TS-LP-06: VS=1G G=512G");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV48X4);
    bool ok = g23_run_one(SUITE_VSATP_MODE, HGATP_MODE_SV48X4,
                          PT_LEVEL_1G, PT_LEVEL_512G);
    TEST_ASSERT("R/W under VS=1G + G=512G", ok);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-LP-07..08: G=256T superpage, VS at 4K/2M
 * Requires: Sv57x4 (256T leaf at level 4 needs 5 levels)
 * =================================================================== */
TEST_REGISTER(test_ts_lp_07_vs4k_g256t);
bool test_ts_lp_07_vs4k_g256t(void)
{
    TEST_BEGIN("TS-LP-07: VS=4K G=256T");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV57X4);
    bool ok = g23_run_one(SUITE_VSATP_MODE, HGATP_MODE_SV57X4,
                          PT_LEVEL_4K, PT_LEVEL_256T);
    TEST_ASSERT("R/W under VS=4K + G=256T", ok);
    HYP_TEST_END();
}

TEST_REGISTER(test_ts_lp_08_vs2m_g256t);
bool test_ts_lp_08_vs2m_g256t(void)
{
    TEST_BEGIN("TS-LP-08: VS=2M G=256T");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(HGATP_MODE_SV57X4);
    bool ok = g23_run_one(SUITE_VSATP_MODE, HGATP_MODE_SV57X4,
                          PT_LEVEL_2M, PT_LEVEL_256T);
    TEST_ASSERT("R/W under VS=2M + G=256T", ok);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-LP-09: VS=512G superpage, G=4K
 * Requires: Sv48+ VS-stage (512G leaf at level 3 needs 4+ levels)
 * =================================================================== */
TEST_REGISTER(test_ts_lp_09_vs512g_g4k);
bool test_ts_lp_09_vs512g_g4k(void)
{
    TEST_BEGIN("TS-LP-09: VS=512G G=4K");
    REQUIRE_VSATP_MODE(SATP_MODE_SV48);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);
    bool ok = g23_run_one(SATP_MODE_SV48, SUITE_HGATP_MODE,
                          PT_LEVEL_512G, PT_LEVEL_4K);
    TEST_ASSERT("R/W under VS=512G + G=4K", ok);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-LP-10: VS=256T superpage, G=4K
 * Requires: Sv57 VS-stage (256T leaf at level 4 needs 5 levels)
 * =================================================================== */
TEST_REGISTER(test_ts_lp_10_vs256t_g4k);
bool test_ts_lp_10_vs256t_g4k(void)
{
    TEST_BEGIN("TS-LP-10: VS=256T G=4K");
    REQUIRE_VSATP_MODE(SATP_MODE_SV57);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);
    bool ok = g23_run_one(SATP_MODE_SV57, SUITE_HGATP_MODE,
                          PT_LEVEL_256T, PT_LEVEL_4K);
    TEST_ASSERT("R/W under VS=256T + G=4K", ok);
    HYP_TEST_END();
}
