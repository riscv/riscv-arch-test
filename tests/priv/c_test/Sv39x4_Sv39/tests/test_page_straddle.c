/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * common/hyp/tests_2stage/test_group16_page_straddle.c
 *
 * Group 16 - Page-boundary straddling under two-stage translation
 * (TS-STRD-01..03).
 *
 * Spec basis (norm:H_straddle, norm:mtval2_htval_virtaddr):
 *   - When a fetch or unaligned data access spans two pages, both
 *     pages are independently translated.
 *   - On guest-page-fault from the second page, stval may be the
 *     page-boundary VA (the start of the second page); htval must
 *     reflect the GPA whose translation faulted (>>2).
 *   - On VS-stage page-fault from the second page, stval is the
 *     original misaligned VA, htval is irrelevant.
 *
 * The test region defined in kernel.ld:
 *   Page 0: test_data_area
 *   Page 1: test_fault_page
 *   Page 2: test_exec_page
 *   Page 3: test_exec_target
 * Group 16 uses test_fault_page (data straddle) or test_exec_page
 * (fetch straddle); the second page is the next 4KB neighbour.
 * =================================================================== */

#ifndef SUITE_HGATP_MODE
#error "SUITE_HGATP_MODE must be defined before including this file"
#endif
#ifndef SUITE_VSATP_MODE
#error "SUITE_VSATP_MODE must be defined before including this file"
#endif


/* G-stage RW (no X), no W bits used for VS-stage W=0 victim. */
#define G16_G_INVALID     (0)
#define G16_G_RU_NOX      (PTE_V|PTE_R|PTE_U|PTE_A|PTE_D)        /* no X, no W */
#define G16_VS_RX_NOW     (PTE_V|PTE_R|PTE_X|PTE_A|PTE_D)        /* no W (VS S-leaf) */

/* ===================================================================
 * VS-mode helpers: misaligned 4-byte load / store across a page edge.
 *
 * lw / sw at va = page_end - 2 issue a single instruction that the
 * hardware decomposes into accesses to two pages (the original page
 * and the next one). We expect the second access to fault.
 * =================================================================== */
static uintptr_t vs_lw_straddle(uintptr_t arg) {
    volatile uint32_t *p = (volatile uint32_t *)arg;
    (void)*p;                       /* lw arg, 0(arg) */
    return trap_get_cause();
}

static uintptr_t vs_sw_straddle(uintptr_t arg) {
    volatile uint32_t *p = (volatile uint32_t *)arg;
    *p = (uint32_t)HYP_TEST_MAGIC;  /* sw to misaligned addr */
    return trap_get_cause();
}

/* ===================================================================
 * TS-STRD-01: 4-byte load that straddles a page edge; the second
 * page is invalid in G-stage. Expect cause=21 (load-guest-fault).
 *
 * NOTE: This test requires hardware support for misaligned memory
 * access. If the platform does not support it (e.g., Spike without
 * Zicclsm), the test will see cause=4 (load-address-misaligned)
 * before reaching the page boundary. We treat this as a SKIP.
 * =================================================================== */
TEST_REGISTER(test_ts_strd_01_load_g_invalid);
bool test_ts_strd_01_load_g_invalid(void) {
    TEST_BEGIN("TS-STRD-01: load straddle, page2 G-invalid -> 21");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t page1 = (uintptr_t)test_fault_page;
    uintptr_t page2 = page1 + 0x1000UL;
    uintptr_t va    = page1 + 0x1000UL - 2UL;     /* lw spans page edge */

    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);
    /* Invalidate the second page in G-stage. VS-stage stays valid. */
    ts2_g_override_4k(&ctx, page2, G16_G_INVALID);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, vs_lw_straddle, va);
    bool fired = trap_was_triggered();
    uintptr_t cause = fired ? trap_get_cause() : 0;
    trap_expect_end();
    two_stage_cleanup(&ctx);
    hyp_reset_state();

    /* If misaligned access is not supported (cause=4), skip the test.
     * This is a platform limitation, not a test failure. */
    if (fired && cause == 4) {
        TEST_ASSERT("misaligned access not supported -> SKIP", true);
        HYP_TEST_END();
    }

    bool ok = (fired && cause == CAUSE_LOAD_GUEST_PAGE_FAULT);
    TEST_ASSERT("cause = load-guest-fault (21)", ok);

    /* norm:mtval2_trapval_other: for a misaligned access causing a
     * guest-page fault, a nonzero mtval2/htval must correspond to the
     * FAULTING PORTION of the access. The straddling load faults on
     * the second page, so a nonzero value must be page2 GPA >> 2
     * (identity-mapped here). Zero is allowed (norm:htval_trapval). */
    uintptr_t hv = trap_get_htval();
    TEST_ASSERT("htval = 0 or faulting-portion GPA>>2 (page2)",
                hv == 0 || hv == (page2 >> 2));

    HYP_TEST_END();
}

/* ===================================================================
 * TS-STRD-02: 32-bit instruction fetch straddles a page edge; the
 * second page lacks X in G-stage. Expect cause=20 (inst-guest-fault).
 *
 * Layout: at test_exec_page + 0xFFE we plant the 4-byte little-
 * endian encoding of `jr ra` (0x00008067). When VS-mode jumps to
 * that VA the CPU fetches 2 bytes from page1 and 2 bytes from page2.
 * page2 = test_exec_target with X stripped at G-stage.
 *
 * NOTE: This test requires hardware support for misaligned instruction
 * fetch. If the platform does not support it, the test will see
 * cause=1 (instruction-address-misaligned) before reaching the page
 * boundary. We treat this as a SKIP.
 * =================================================================== */
TEST_REGISTER(test_ts_strd_02_fetch_g_no_x);
bool test_ts_strd_02_fetch_g_no_x(void) {
    TEST_BEGIN("TS-STRD-02: fetch straddle, page2 G no-X -> 20");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t page1 = (uintptr_t)test_exec_page;
    uintptr_t page2 = page1 + 0x1000UL;            /* == test_exec_target */
    uintptr_t va    = page1 + 0x1000UL - 2UL;      /* fetch spans page edge */

    /* Plant a 32-bit `jr ra` (0x00008067) at va so a successful fetch
     * would just return; we never expect that path because page2
     * lacks X, but the recovery label in test_vs_exec_expect_fault
     * pre-loads ra with the post-jump anchor either way.
     *
     * Use aligned 16-bit stores to avoid misaligned-access traps on
     * platforms that don't support them. */
    volatile uint16_t *p16 = (volatile uint16_t *)va;
    p16[0] = 0x8067;  /* low 16 bits of jr ra */
    p16[1] = 0x0000;  /* high 16 bits of jr ra */

    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);
    /* Strip X in G-stage on page2 only. */
    ts2_g_override_4k(&ctx, page2, G16_G_RU_NOX);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_exec_expect_fault, va);
    bool fired = trap_was_triggered();
    uintptr_t cause = fired ? trap_get_cause() : 0;
    trap_expect_end();
    two_stage_cleanup(&ctx);
    hyp_reset_state();

    /* If misaligned fetch is not supported (cause=1), skip the test.
     * This is a platform limitation, not a test failure. */
    if (fired && cause == 1) {
        TEST_ASSERT("misaligned fetch not supported -> SKIP", true);
        HYP_TEST_END();
    }

    bool ok = (fired && cause == CAUSE_INST_GUEST_PAGE_FAULT);
    TEST_ASSERT("cause = inst-guest-fault (20)", ok);

    /* norm:mtval2_trapval_other: for an instruction guest-page fault
     * (variable-length fetch straddling the page edge), a nonzero
     * mtval2/htval must correspond to the faulting portion of the
     * instruction, i.e. the second page here. Zero is allowed. */
    uintptr_t hv = trap_get_htval();
    TEST_ASSERT("htval = 0 or faulting-portion GPA>>2 (page2)",
                hv == 0 || hv == (page2 >> 2));

    HYP_TEST_END();
}

/* ===================================================================
 * TS-STRD-03: 4-byte store straddles a page edge; the second page
 * has no W in VS-stage. Expect cause=15 (store-page-fault, VS-stage).
 *
 * NOTE: This test requires hardware support for misaligned memory
 * access. If the platform does not support it, the test will see
 * cause=6 (store-address-misaligned) before reaching the page
 * boundary. We treat this as a SKIP.
 * =================================================================== */
TEST_REGISTER(test_ts_strd_03_store_vs_no_w);
bool test_ts_strd_03_store_vs_no_w(void) {
    TEST_BEGIN("TS-STRD-03: store straddle, page2 VS no-W -> 15");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t page1 = (uintptr_t)test_fault_page;
    uintptr_t page2 = page1 + 0x1000UL;
    uintptr_t va    = page1 + 0x1000UL - 2UL;

    /* Build full identity, then override page2's VS-stage leaf to
     * R+X (no W). G-stage stays full RWX so any G-stage fault is
     * impossible -> the trap must be a VS-stage page-fault. */
    ts2_setup_with_vs_victim(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE,
                             page2, G16_VS_RX_NOW);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, vs_sw_straddle, va);
    bool fired = trap_was_triggered();
    uintptr_t cause = fired ? trap_get_cause() : 0;
    trap_expect_end();
    two_stage_cleanup(&ctx);
    hyp_reset_state();

    /* If misaligned access is not supported (cause=6), skip the test.
     * This is a platform limitation, not a test failure. */
    if (fired && cause == 6) {
        TEST_ASSERT("misaligned store not supported -> SKIP", true);
        HYP_TEST_END();
    }

    bool ok = (fired && cause == CAUSE_STORE_PAGE_FAULT);
    TEST_ASSERT("cause = store-page-fault (15)", ok);
    HYP_TEST_END();
}
