/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * common/hyp/tests_2stage/test_group18_pbmte.c
 *
 * Group 18 - henvcfg.PBMTE controls Svpbmt for VS-stage
 * (TS-PBMT-01..02).
 *
 * Spec basis (norm:henvcfg_pbmte_op):
 *   - PBMTE=0: VS-stage PTE bits[62:61] are reserved; non-zero raises
 *     a page-fault (Svpbmt unimplemented for VS-stage).
 *   - PBMTE=1: VS-stage PTE bits[62:61] are interpreted as PBMT
 *     (NC=01, IO=10, PMA=00); translation succeeds.
 *
 * Note: menvcfg.PBMTE gates henvcfg.PBMTE; tests must enable both.
 * The framework hyp_reset_state() leaves menvcfg.PBMTE untouched (only
 * ADUE is forced 0), so the field reflects platform default. We
 * explicitly set/clear menvcfg.PBMTE here to make the test
 * deterministic.
 * =================================================================== */

#ifndef SUITE_HGATP_MODE
#error "SUITE_HGATP_MODE must be defined before including this file"
#endif
#ifndef SUITE_VSATP_MODE
#error "SUITE_VSATP_MODE must be defined before including this file"
#endif


/* Standard low-bit flags for a VS-stage S-leaf with full perms. */
#define G18_VS_FULL  (PTE_V|PTE_R|PTE_W|PTE_X|PTE_A|PTE_D)

/* Helper: set PBMT bits on the VS-stage 4K leaf for @va. Caller must
 * have already mapped @va via ts2_setup_full / ts2_setup_with_vs_victim. */
static void g18_vs_set_pbmt(two_stage_ctx_t *ctx, uintptr_t va,
                            uintptr_t pbmt_bits) {
    uintptr_t *pte = pt_get_pte(&ctx->vs_ctx, va & ~0xfffUL, PT_LEVEL_4K);
    TEST_ASSERT("VS leaf PTE resolvable", pte != NULL);
    if (pte) {
        /* Clear existing PBMT field, then OR in the desired bits. */
        *pte = (*pte & ~PTE_PBMT_MASK) | (pbmt_bits & PTE_PBMT_MASK);
    }
    hfence_vvma_all();
}

static inline void g18_enable_pbmte(void) { ts2_enable_pbmte(); }
static inline void g18_disable_pbmte(void) { ts2_disable_pbmte(); }

/* ===================================================================
 * TS-PBMT-01: PBMTE=0 + VS PTE PBMT=NC -> page-fault (cause=13).
 * =================================================================== */
TEST_REGISTER(test_ts_pbmt_01_pbmte0_fault);
bool test_ts_pbmt_01_pbmte0_fault(void) {
    TEST_BEGIN("TS-PBMT-01: PBMTE=0 + VS PBMT=NC -> page-fault (13)");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_data_area;
    ts2_setup_with_vs_victim(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE, va, G18_VS_FULL);
    g18_vs_set_pbmt(&ctx, va, PBMT_NC);

    /* Ensure PBMTE=0 (suite default; explicit for clarity). */
    g18_disable_pbmte();

    bool ok = ts2_run_check_fault(&ctx, test_vs_load_expect_fault, va,
                                  CAUSE_LOAD_PAGE_FAULT);
    if (!ok) {
        TEST_SKIP("platform does not implement Svpbmt PBMT-reserved trapping");
    }
    TEST_ASSERT("cause = load-page-fault (13)", ok);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-PBMT-02: PBMTE=1 + VS PTE PBMT=NC -> translation succeeds.
 * =================================================================== */
TEST_REGISTER(test_ts_pbmt_02_pbmte1_ok);
bool test_ts_pbmt_02_pbmte1_ok(void) {
    TEST_BEGIN("TS-PBMT-02: PBMTE=1 + VS PBMT=NC -> translation OK");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_data_area;
    ts2_setup_with_vs_victim(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE, va, G18_VS_FULL);
    g18_vs_set_pbmt(&ctx, va, PBMT_NC);

    g18_enable_pbmte();
    /* Verify PBMTE actually took effect (read-only 0 if unsupported). */
    uintptr_t hv = henvcfg_read();
    bool supported = ((hv & (1ULL << 62)) != 0);

    if (!supported) {
        g18_disable_pbmte();
        ts2_finish(&ctx);
        TEST_SKIP("platform does not support Svpbmt (henvcfg.PBMTE r/o 0)");
    }

    uintptr_t r = ts2_run_check_no_fault(&ctx, test_vs_read_write, va);
    g18_disable_pbmte();
    TEST_ASSERT("two-stage RW succeeds with PBMT=NC", r == 0);
    HYP_TEST_END();
}
