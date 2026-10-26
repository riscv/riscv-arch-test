/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * test_granular_matrix.c
 *
 * VS×G 笛卡尔积粒度矩阵测试
 *
 * 编译期根据 SUITE_VSATP_MODE / SUITE_HGATP_MODE 裁剪，只注册
 * 当前目录页表模式实际支持的粒度组合：
 *   - Sv39  / Sv39x4  → max level = 1G   → 3×3 =  9 用例
 *   - Sv48  / Sv48x4  → max level = 512G → 4×4 = 16 用例
 *   - Sv57  / Sv57x4  → max level = 256T → 5×5 = 25 用例
 *
 * 混合目录（如 Sv39_Sv57x4）取 min(VS_rows, G_cols) 的笛卡尔积。
 *
 * 验证手段：ts2_setup_granular + ts2_run_check_no_fault(test_vs_read_write)
 * =================================================================== */

#include "two_stage_helpers.h"

/* ---------------------------------------------------------------
 * 编译期最大 level 常量（利用 MODE 值 8/9/10 → level 2/3/4 的映射）
 * --------------------------------------------------------------- */
#define _SUITE_VS_MAX  (SUITE_VSATP_MODE - 6)
#define _SUITE_G_MAX   (SUITE_HGATP_MODE - 6)

/* 单条粒度组合执行函数 */
static bool gm_run_one(int vs_level, int g_level)
{
    two_stage_ctx_t ctx;
    ts2_setup_granular(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE,
                       vs_level, g_level);

    uintptr_t va = (uintptr_t)test_data_area;
    uintptr_t r  = ts2_run_check_no_fault(&ctx, test_vs_read_write, va);
    bool ok = (r == 0);
    ts2_finish(&ctx);
    return ok;
}

/* 平台探测守门：若硬件/模拟器不支持该 mode 则 SKIP */
#define MATRIX_GUARD() do { \
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE); \
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE); \
} while (0)

/* 单条用例宏 */
#define MATRIX_CASE(VL, GL, ID, NAME)                                    \
    TEST_REGISTER(test_gm_##ID);                                          \
    bool test_gm_##ID(void)                                               \
    {                                                                     \
        TEST_BEGIN("TS-GM-" #ID ": VS=" NAME);                            \
        MATRIX_GUARD();                                                   \
        bool ok = gm_run_one((VL), (GL));                                 \
        TEST_ASSERT("two-stage R/W under " NAME, ok);                     \
        HYP_TEST_END();                                                   \
    }

/* ===================================================================
 * 5×5 粒度矩阵 — 编译期按 _SUITE_VS_MAX / _SUITE_G_MAX 裁剪
 * =================================================================== */

/* --- row 1: VS = 4K (level 0) — 所有 mode 都支持 --- */
MATRIX_CASE(PT_LEVEL_4K, PT_LEVEL_4K, 11, "4K   / G=4K")
MATRIX_CASE(PT_LEVEL_4K, PT_LEVEL_2M, 12, "4K   / G=2M")
MATRIX_CASE(PT_LEVEL_4K, PT_LEVEL_1G, 13, "4K   / G=1G")
#if _SUITE_G_MAX >= PT_LEVEL_512G
MATRIX_CASE(PT_LEVEL_4K, PT_LEVEL_512G, 14, "4K   / G=512G")
#endif
#if _SUITE_G_MAX >= PT_LEVEL_256T
MATRIX_CASE(PT_LEVEL_4K, PT_LEVEL_256T, 15, "4K   / G=256T")
#endif

/* --- row 2: VS = 2M (level 1) — 所有 mode 都支持 --- */
MATRIX_CASE(PT_LEVEL_2M, PT_LEVEL_4K, 21, "2M   / G=4K")
MATRIX_CASE(PT_LEVEL_2M, PT_LEVEL_2M, 22, "2M   / G=2M")
MATRIX_CASE(PT_LEVEL_2M, PT_LEVEL_1G, 23, "2M   / G=1G")
#if _SUITE_G_MAX >= PT_LEVEL_512G
MATRIX_CASE(PT_LEVEL_2M, PT_LEVEL_512G, 24, "2M   / G=512G")
#endif
#if _SUITE_G_MAX >= PT_LEVEL_256T
MATRIX_CASE(PT_LEVEL_2M, PT_LEVEL_256T, 25, "2M   / G=256T")
#endif

/* --- row 3: VS = 1G (level 2) — 所有 mode 都支持 --- */
MATRIX_CASE(PT_LEVEL_1G, PT_LEVEL_4K, 31, "1G   / G=4K")
MATRIX_CASE(PT_LEVEL_1G, PT_LEVEL_2M, 32, "1G   / G=2M")
MATRIX_CASE(PT_LEVEL_1G, PT_LEVEL_1G, 33, "1G   / G=1G")
#if _SUITE_G_MAX >= PT_LEVEL_512G
MATRIX_CASE(PT_LEVEL_1G, PT_LEVEL_512G, 34, "1G   / G=512G")
#endif
#if _SUITE_G_MAX >= PT_LEVEL_256T
MATRIX_CASE(PT_LEVEL_1G, PT_LEVEL_256T, 35, "1G   / G=256T")
#endif

/* --- row 4: VS = 512G (level 3) — 仅 Sv48/Sv57 --- */
#if _SUITE_VS_MAX >= PT_LEVEL_512G
MATRIX_CASE(PT_LEVEL_512G, PT_LEVEL_4K, 41, "512G / G=4K")
MATRIX_CASE(PT_LEVEL_512G, PT_LEVEL_2M, 42, "512G / G=2M")
MATRIX_CASE(PT_LEVEL_512G, PT_LEVEL_1G, 43, "512G / G=1G")
#if _SUITE_G_MAX >= PT_LEVEL_512G
MATRIX_CASE(PT_LEVEL_512G, PT_LEVEL_512G, 44, "512G / G=512G")
#endif
#if _SUITE_G_MAX >= PT_LEVEL_256T
MATRIX_CASE(PT_LEVEL_512G, PT_LEVEL_256T, 45, "512G / G=256T")
#endif
#endif /* _SUITE_VS_MAX >= PT_LEVEL_512G */

/* --- row 5: VS = 256T (level 4) — 仅 Sv57 --- */
#if _SUITE_VS_MAX >= PT_LEVEL_256T
MATRIX_CASE(PT_LEVEL_256T, PT_LEVEL_4K, 51, "256T / G=4K")
MATRIX_CASE(PT_LEVEL_256T, PT_LEVEL_2M, 52, "256T / G=2M")
MATRIX_CASE(PT_LEVEL_256T, PT_LEVEL_1G, 53, "256T / G=1G")
#if _SUITE_G_MAX >= PT_LEVEL_512G
MATRIX_CASE(PT_LEVEL_256T, PT_LEVEL_512G, 54, "256T / G=512G")
#endif
#if _SUITE_G_MAX >= PT_LEVEL_256T
MATRIX_CASE(PT_LEVEL_256T, PT_LEVEL_256T, 55, "256T / G=256T")
#endif
#endif /* _SUITE_VS_MAX >= PT_LEVEL_256T */
