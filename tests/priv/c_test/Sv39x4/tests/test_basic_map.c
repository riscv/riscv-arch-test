/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Sv*x4 basic mapping tests
 *
 * Spec anchors:
 *   norm:gstage_translation - G-stage walks GPA -> SPA per Sv*x4
 *   norm:gstage_pte_format  - PTE format identical to Sv*: V/R/W/X/U/A/D
 *
 * Common tests (all modes):
 *   GMAP-4K:  leaf at 4KB level
 *   GMAP-2M:  leaf at 2MB level (superpage)
 *   GMAP-1G:  leaf at 1GB level (superpage)
 *
 * Sv48x4-only:
 *   G48-MAP-01: 512GB terapage leaf (4 levels of Sv48x4, leaf at top)
 *
 *   NOTE on 512GB terapage: the full 512GB range cannot be physically
 *   backed on QEMU virt (≤ a few GB of RAM). Instead we install a
 *   single 512GB leaf at GPA=0 which, in identity mode, covers the
 *   full low address space (including PLATFORM_MEM_BASE, UART, and
 *   the test region). We then only access addresses that are backed
 *   by real physical memory (test_data_area), verifying the 512GB
 *   translation path.
 * =================================================================== */

static bool _gmap_run_one(const char *what, int leaf_level, uintptr_t pgsz) {
    gpt_pool_reset();
    two_stage_ctx_t ctx;
    two_stage_init(&ctx, SATP_MODE_BARE, SUITE_HGATP_MODE);

    uintptr_t map_base = PLATFORM_MEM_BASE & ~(pgsz - 1);
    uintptr_t map_size = (((uintptr_t)__vm_test_region_end - map_base
                          + pgsz - 1) & ~(pgsz - 1));

    /* For 1GB pages cover at least the first 1GB starting at MEM_BASE. */
    if (leaf_level == PT_LEVEL_1G && map_size < (1UL << 30))
        map_size = (1UL << 30);

    int rc = two_stage_setup_identity(&ctx, map_base, map_size,
                                      G_FLAGS_RWXU_AD, leaf_level);
    if (rc != 0) {
        LOG_E("[%s] identity mapping failed\n", what);
        two_stage_cleanup(&ctx);
        return false;
    }

    uintptr_t target = (uintptr_t)test_data_area;
    *(volatile uint64_t *)target = 0;

    uintptr_t r = two_stage_run_in_vs(&ctx, test_vs_read_write, target);
    bool ok = (r == 0);
    if (!ok)
        LOG_E("[%s] vs read/write returned 0x%lx\n", what,
              (unsigned long)r);

    two_stage_cleanup(&ctx);
    hyp_reset_state();
    return ok;
}

/* ------------------------------------------------------------------ */
/* Common tests: 4KB / 2MB / 1GB leaf mappings (all modes)            */
/* ------------------------------------------------------------------ */

/* GMAP-4K: 4KB-leaf identity mapping */
TEST_REGISTER(test_gmap_4k);
bool test_gmap_4k(void) {
    TEST_BEGIN("GMAP-4K: Sv*x4 4KB leaf mapping");
    bool ok = _gmap_run_one("4KB", PT_LEVEL_4K, PAGE_SIZE_4K);
    TEST_ASSERT("VS-mode r/w via 4KB G-stage leaf succeeds", ok);
    HYP_TEST_END();
}

/* GMAP-2M: 2MB-leaf identity mapping (superpage) */
TEST_REGISTER(test_gmap_2m);
bool test_gmap_2m(void) {
    TEST_BEGIN("GMAP-2M: Sv*x4 2MB leaf mapping (superpage)");
    bool ok = _gmap_run_one("2MB", PT_LEVEL_2M, PAGE_SIZE_2M);
    TEST_ASSERT("VS-mode r/w via 2MB G-stage leaf succeeds", ok);
    HYP_TEST_END();
}

/* GMAP-1G: 1GB-leaf identity mapping (superpage) */
TEST_REGISTER(test_gmap_1g);
bool test_gmap_1g(void) {
    TEST_BEGIN("GMAP-1G: Sv*x4 1GB leaf mapping (superpage)");
    bool ok = _gmap_run_one("1GB", PT_LEVEL_1G, PAGE_SIZE_1G);
    TEST_ASSERT("VS-mode r/w via 1GB G-stage leaf succeeds", ok);
    HYP_TEST_END();
}

/* ------------------------------------------------------------------ */
/* Sv48x4-only: 512GB terapage leaf mapping                          */
/* ------------------------------------------------------------------ */
#if SUITE_HGATP_MODE == HGATP_MODE_SV48X4

/* G48-MAP-01: 512GB terapage — install a single leaf covering [0,512GB). */
TEST_REGISTER(test_g48_map_01_512g);
bool test_g48_map_01_512g(void) {
    TEST_BEGIN("G48-MAP-01: Sv48x4 512GB terapage leaf mapping");

    gpt_pool_reset();
    two_stage_ctx_t ctx;
    two_stage_init(&ctx, SATP_MODE_BARE, HGATP_MODE_SV48X4);

    /* Single 512GB leaf at GPA=0 → SPA=0. Covers PLATFORM_MEM_BASE
     * and the UART (both within the first 512GB). */
    int rc = gpt_map_page(&ctx.g_ctx, 0UL, 0UL,
                          G_FLAGS_RWXU_AD, PT_LEVEL_512G);
    if (rc != 0) {
        LOG_E("512GB leaf install failed (rc=%d)\n", rc);
        two_stage_cleanup(&ctx);
        hyp_reset_state();
        TEST_ASSERT("install 512GB leaf", false);
        HYP_TEST_END();
    }

    uintptr_t target = (uintptr_t)test_data_area;
    *(volatile uint64_t *)target = 0;
    uintptr_t r = two_stage_run_in_vs(&ctx, test_vs_read_write, target);
    TEST_ASSERT("VS-mode r/w via 512GB G-stage leaf succeeds", r == 0);

    two_stage_cleanup(&ctx);
    hyp_reset_state();
    HYP_TEST_END();
}

#endif /* SUITE_HGATP_MODE == HGATP_MODE_SV48X4 */
