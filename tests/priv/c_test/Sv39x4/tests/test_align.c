/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 11: G-stage superpage alignment check
 *
 * Spec anchors:
 *   norm:gstage_superpage_align - A leaf PTE at level > 0 whose PPN
 *                                 lower bits are non-zero is a
 *                                 misaligned superpage and triggers
 *                                 guest-page-fault.
 *
 * Common tests (all modes):
 *   GALIGN-01: 1GB leaf with PPN[1:0] != 0 -> load gpf (cause 21)
 *   GALIGN-02: 2MB leaf with PPN[0]   != 0 -> load gpf (cause 21)
 *   GALIGN-05: aligned 2MB leaf            -> success (load+store ok)
 *
 * Sv48x4/Sv57x4 only:
 *   GALIGN-03: 512GB leaf with PPN[0] != 0 -> load gpf (cause 21)
 *
 * Sv57x4 only:
 *   GALIGN-04: 256TB leaf with PPN[0] != 0 -> load gpf (cause 21)
 * =================================================================== */

/* Build a G-stage with low-mem identity (2MB) + a single leaf at the
 * supplied level whose PTE bits exactly equal `raw_pte`. */
static void _setup_with_raw_leaf(two_stage_ctx_t *ctx,
                                 uintptr_t leaf_gpa,
                                 int       leaf_level,
                                 uintptr_t raw_pte_flags,
                                 uintptr_t raw_ppn)
{
    gpt_pool_reset();
    two_stage_init(ctx, SATP_MODE_BARE, SUITE_HGATP_MODE);

    /* Identity-map kernel/UART at 2MB so the trampoline can run. */
    uintptr_t lo_base = PLATFORM_MEM_BASE & ~(PAGE_SIZE_2M - 1);
    uintptr_t lo_end  = (uintptr_t)__vm_test_region_start
                        & ~(PAGE_SIZE_2M - 1);
    for (uintptr_t a = lo_base; a < lo_end; a += PAGE_SIZE_2M)
        (void)gpt_map_page(&ctx->g_ctx, a, a, G_FLAGS_RWXU_AD, PT_LEVEL_2M);

    uintptr_t uart_pg = PLATFORM_UART0_BASE & ~(PAGE_SIZE_4K - 1);
    if (uart_pg < lo_base || uart_pg >= lo_end) {
        uintptr_t uart_flags = PTE_V | PTE_R | PTE_W | PTE_U | PTE_A | PTE_D;
        (void)gpt_map_page(&ctx->g_ctx, uart_pg, uart_pg,
                           uart_flags, PT_LEVEL_4K);
    }

    /* Install the (possibly misaligned) superpage. */
    (void)gpt_map_page(&ctx->g_ctx, leaf_gpa, raw_ppn << 12,
                       raw_pte_flags, leaf_level);
}

/* GALIGN-01: 1GB superpage with low PPN bits set -> guest-page-fault */
TEST_REGISTER(test_galign_01_1g_misaligned);
bool test_galign_01_1g_misaligned(void) {
    TEST_BEGIN("GALIGN-01: 1GB misaligned G-stage superpage -> load gpf");

    two_stage_ctx_t ctx;
    uintptr_t target = (uintptr_t)test_fault_page;
    uintptr_t gpa_1g = target & ~(PAGE_SIZE_1G - 1);
    uintptr_t bad_ppn = (gpa_1g >> 12) | 0x1UL;

    _setup_with_raw_leaf(&ctx, gpa_1g, PT_LEVEL_1G,
                         G_FLAGS_RWXU_AD, bad_ppn);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_load_expect_fault, target);
    bool fired = trap_was_triggered();
    uintptr_t cause = fired ? trap_get_cause() : 0;
    trap_expect_end();

    two_stage_cleanup(&ctx);
    hyp_reset_state();

    TEST_ASSERT("misaligned 1GB triggers fault", fired);
    TEST_ASSERT_EQ("misaligned 1GB cause = load gpf",
                   cause, CAUSE_LOAD_GUEST_PAGE_FAULT);
    HYP_TEST_END();
}

/* GALIGN-02: 2MB superpage with PPN[0] non-zero -> guest-page-fault */
TEST_REGISTER(test_galign_02_2m_misaligned);
bool test_galign_02_2m_misaligned(void) {
    TEST_BEGIN("GALIGN-02: 2MB misaligned G-stage superpage -> load gpf");

    two_stage_ctx_t ctx;
    uintptr_t target = (uintptr_t)test_fault_page;
    uintptr_t gpa_2m = target & ~(PAGE_SIZE_2M - 1);
    uintptr_t bad_ppn = (gpa_2m >> 12) | 0x1UL;

    _setup_with_raw_leaf(&ctx, gpa_2m, PT_LEVEL_2M,
                         G_FLAGS_RWXU_AD, bad_ppn);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_load_expect_fault, target);
    bool fired = trap_was_triggered();
    uintptr_t cause = fired ? trap_get_cause() : 0;
    trap_expect_end();

    two_stage_cleanup(&ctx);
    hyp_reset_state();

    TEST_ASSERT("misaligned 2MB triggers fault", fired);
    TEST_ASSERT_EQ("misaligned 2MB cause = load gpf",
                   cause, CAUSE_LOAD_GUEST_PAGE_FAULT);
    HYP_TEST_END();
}

/* ------------------------------------------------------------------ */
/* Sv48x4/Sv57x4 only: 512GB misaligned superpage test               */
/* ------------------------------------------------------------------ */
#if SUITE_HGATP_MODE == HGATP_MODE_SV48X4 || SUITE_HGATP_MODE == HGATP_MODE_SV57X4

/* GALIGN-03: 512GB superpage with PPN[0] non-zero -> guest-page-fault */
TEST_REGISTER(test_galign_03_512g_misaligned);
bool test_galign_03_512g_misaligned(void) {
    TEST_BEGIN("GALIGN-03: 512GB misaligned G-stage superpage -> load gpf");

    two_stage_ctx_t ctx;
    gpt_pool_reset();
    two_stage_init(&ctx, SATP_MODE_BARE, SUITE_HGATP_MODE);

    /* Low region (kernel / UART / test region) identity at 2MB. */
    uintptr_t lo_base = PLATFORM_MEM_BASE & ~(PAGE_SIZE_2M - 1);
    uintptr_t lo_end  = ((uintptr_t)__vm_test_region_end
                         + PAGE_SIZE_2M - 1) & ~(PAGE_SIZE_2M - 1);
    for (uintptr_t a = lo_base; a < lo_end; a += PAGE_SIZE_2M)
        (void)gpt_map_page(&ctx.g_ctx, a, a, G_FLAGS_RWXU_AD, PT_LEVEL_2M);

    uintptr_t uart_pg = PLATFORM_UART0_BASE & ~(PAGE_SIZE_4K - 1);
    if (uart_pg < lo_base || uart_pg >= lo_end) {
        (void)gpt_map_page(&ctx.g_ctx, uart_pg, uart_pg,
                           PTE_V|PTE_R|PTE_W|PTE_U|PTE_A|PTE_D,
                           PT_LEVEL_4K);
    }

    /* Target at 512GB-aligned GPA. Force PPN[0]=1 to make it
     * misaligned; a legal 512GB leaf requires PPN[26:0]==0. */
    uintptr_t tera = 512UL * 1024UL * 1024UL * 1024UL; /* 512GB */
    uintptr_t bad_ppn = (tera >> 12) | 0x1UL;
    (void)gpt_map_page(&ctx.g_ctx, tera, bad_ppn << 12,
                       G_FLAGS_RWXU_AD, PT_LEVEL_512G);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_load_expect_fault, tera);
    bool fired = trap_was_triggered();
    uintptr_t cause = fired ? trap_get_cause() : 0;
    trap_expect_end();

    two_stage_cleanup(&ctx);
    hyp_reset_state();

    TEST_ASSERT("misaligned 512GB triggers fault", fired);
    TEST_ASSERT_EQ("misaligned 512GB cause = load gpf",
                   cause, CAUSE_LOAD_GUEST_PAGE_FAULT);
    HYP_TEST_END();
}

#endif /* SV48X4 || SV57X4 */

/* ------------------------------------------------------------------ */
/* Sv57x4 only: 256TB misaligned superpage test                      */
/* ------------------------------------------------------------------ */
#if SUITE_HGATP_MODE == HGATP_MODE_SV57X4

/* GALIGN-04: 256TB superpage with PPN[0] non-zero -> guest-page-fault */
TEST_REGISTER(test_galign_04_256t_misaligned);
bool test_galign_04_256t_misaligned(void) {
    TEST_BEGIN("GALIGN-04: 256TB misaligned G-stage superpage -> load gpf");

    two_stage_ctx_t ctx;
    gpt_pool_reset();
    two_stage_init(&ctx, SATP_MODE_BARE, HGATP_MODE_SV57X4);

    /* Low region (kernel / UART / test region) identity at 2MB. */
    uintptr_t lo_base = PLATFORM_MEM_BASE & ~(PAGE_SIZE_2M - 1);
    uintptr_t lo_end  = ((uintptr_t)__vm_test_region_end
                         + PAGE_SIZE_2M - 1) & ~(PAGE_SIZE_2M - 1);
    for (uintptr_t a = lo_base; a < lo_end; a += PAGE_SIZE_2M)
        (void)gpt_map_page(&ctx.g_ctx, a, a, G_FLAGS_RWXU_AD, PT_LEVEL_2M);

    uintptr_t uart_pg = PLATFORM_UART0_BASE & ~(PAGE_SIZE_4K - 1);
    if (uart_pg < lo_base || uart_pg >= lo_end) {
        (void)gpt_map_page(&ctx.g_ctx, uart_pg, uart_pg,
                           PTE_V|PTE_R|PTE_W|PTE_U|PTE_A|PTE_D,
                           PT_LEVEL_4K);
    }

    /* Target at 256TB-aligned GPA. Force PPN[0]=1 to make it
     * misaligned; a legal 256TB leaf requires PPN[35:0]==0. */
    uintptr_t peta = 256UL * 1024UL * 1024UL * 1024UL * 1024UL; /* 256TB */
    uintptr_t bad_ppn = (peta >> 12) | 0x1UL;
    (void)gpt_map_page(&ctx.g_ctx, peta, bad_ppn << 12,
                       G_FLAGS_RWXU_AD, PT_LEVEL_256T);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_load_expect_fault, peta);
    bool fired = trap_was_triggered();
    uintptr_t cause = fired ? trap_get_cause() : 0;
    trap_expect_end();

    two_stage_cleanup(&ctx);
    hyp_reset_state();

    TEST_ASSERT("misaligned 256TB triggers fault", fired);
    TEST_ASSERT_EQ("misaligned 256TB cause = load gpf",
                   cause, CAUSE_LOAD_GUEST_PAGE_FAULT);
    HYP_TEST_END();
}

#endif /* SV57X4 */

/* GALIGN-05: aligned 2MB superpage -> normal r/w */
TEST_REGISTER(test_galign_05_aligned_ok);
bool test_galign_05_aligned_ok(void) {
    TEST_BEGIN("GALIGN-05: aligned 2MB G-stage superpage permits r/w");

    two_stage_ctx_t ctx;
    gpt_pool_reset();
    two_stage_init(&ctx, SATP_MODE_BARE, SUITE_HGATP_MODE);

    /* Identity-map kernel/UART at 2MB. */
    uintptr_t lo_base = PLATFORM_MEM_BASE & ~(PAGE_SIZE_2M - 1);
    uintptr_t lo_end  = (uintptr_t)__vm_test_region_start
                        & ~(PAGE_SIZE_2M - 1);
    for (uintptr_t a = lo_base; a < lo_end; a += PAGE_SIZE_2M)
        (void)gpt_map_page(&ctx.g_ctx, a, a, G_FLAGS_RWXU_AD, PT_LEVEL_2M);

    uintptr_t uart_pg = PLATFORM_UART0_BASE & ~(PAGE_SIZE_4K - 1);
    if (uart_pg < lo_base || uart_pg >= lo_end) {
        uintptr_t uart_flags = PTE_V | PTE_R | PTE_W | PTE_U | PTE_A | PTE_D;
        (void)gpt_map_page(&ctx.g_ctx, uart_pg, uart_pg,
                           uart_flags, PT_LEVEL_4K);
    }

    /* Map the entire test region as a single aligned 2MB superpage. */
    uintptr_t target = (uintptr_t)test_fault_page;
    uintptr_t gpa_2m = target & ~(PAGE_SIZE_2M - 1);
    int rc = gpt_map_page(&ctx.g_ctx, gpa_2m, gpa_2m,
                          G_FLAGS_RWXU_AD, PT_LEVEL_2M);
    TEST_ASSERT("2MB leaf install ok", rc == 0);

    *(volatile uint64_t *)test_fault_page = 0;
    uintptr_t r = two_stage_run_in_vs(&ctx, test_vs_read_write, target);
    TEST_ASSERT("aligned 2MB r/w returns 0", r == 0);

    two_stage_cleanup(&ctx);
    HYP_TEST_END();
}
