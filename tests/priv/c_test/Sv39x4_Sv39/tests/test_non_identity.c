/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * common/hyp/tests_2stage/test_group05_non_identity.c
 *
 * Group 5 - Non-identity two-stage mappings (TS-NID-01..04)
 *
 * Validates that:
 *   - VS-stage outputs a GPA distinct from VA;
 *   - G-stage  outputs an SPA distinct from GPA;
 *   - Both stages can simultaneously redirect;
 *   - Multiple consecutive 4K pages with distinct redirects keep
 *     data isolated end-to-end.
 *
 * The suite glue (e.g. Sv39x4/tests/test_register.c) defines the
 * default modes via SUITE_HGATP_MODE / SUITE_VSATP_MODE before
 * including this file.
 *
 * NOTE: VS-mode in this codebase is exercised at S-level; therefore
 * VS-stage leaf PTEs must use VS_FLAGS_RWX_S_AD (U=0). G-stage leaf
 * PTEs always use G_FLAGS_RWXU_AD because G-stage views every guest
 * access as U-mode.
 * =================================================================== */

#ifndef SUITE_HGATP_MODE
#error "SUITE_HGATP_MODE must be defined before including this file"
#endif
#ifndef SUITE_VSATP_MODE
#error "SUITE_VSATP_MODE must be defined before including this file"
#endif


/* Magic values written by VS-mode under M-mode supervision. The M-mode
 * caller pre-clears each candidate physical slot, then inspects all of
 * them to confirm the write landed at the expected SPA only. */
#define G5_MAGIC_0   0x5151515151515151ULL
#define G5_MAGIC_1   0xA1A1A1A1A1A1A1A1ULL
#define G5_MAGIC_2   0xB2B2B2B2B2B2B2B2ULL
#define G5_MAGIC_3   0xC3C3C3C3C3C3C3C3ULL

/* ----- file-scope helpers (static; private to this TU) ----- */

static inline void g5_clear4(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d) {
    *(volatile uint64_t *)a = 0;
    *(volatile uint64_t *)b = 0;
    *(volatile uint64_t *)c = 0;
    *(volatile uint64_t *)d = 0;
}

/* Override an existing VS-stage 4K leaf PTE: VA -> GPA, with given flags.
 * Caller must have already mapped VA at 4K granularity. */
static void g5_redirect_vs(two_stage_ctx_t *ctx, uintptr_t va, uintptr_t gpa) {
    if (ctx->vs_mode == SATP_MODE_BARE) return;
    uintptr_t va_pg  = va  & ~(PAGE_SIZE_4K - 1);
    uintptr_t gpa_pg = gpa & ~(PAGE_SIZE_4K - 1);
    uintptr_t *pte = pt_get_pte(&ctx->vs_ctx, va_pg, PT_LEVEL_4K);
    if (pte != NULL) {
        *pte = ((gpa_pg >> 12) << 10) | VS_FLAGS_RWX_S_AD;
    }
}

/* Run a single VS-mode write and verify the magic lands at the expected
 * SPA only, with all other candidate SPAs untouched. */
static bool g5_write_and_check(two_stage_ctx_t *ctx, uintptr_t va,
                               uintptr_t expect_spa,
                               const uintptr_t *other_spas, int n_others)
{
    /* test_vs_store writes HYP_TEST_MAGIC; we use it to keep the
     * VS-mode side stateless (no need to thread arbitrary magics in). */
    uintptr_t r = ts2_run_check_no_fault(ctx, test_vs_store, va);
    if (r != 0) {
        LOG_E("VS-mode store returned %lu (expected 0)\n",
              (unsigned long)r);
        return false;
    }
    if (*(volatile uint64_t *)expect_spa != HYP_TEST_MAGIC) {
        LOG_E("expected SPA 0x%lx not modified (got 0x%lx)\n",
              (unsigned long)expect_spa,
              (unsigned long)*(volatile uint64_t *)expect_spa);
        return false;
    }
    for (int i = 0; i < n_others; i++) {
        if (*(volatile uint64_t *)other_spas[i] != 0) {
            LOG_E("unexpected modification at SPA 0x%lx (got 0x%lx)\n",
                  (unsigned long)other_spas[i],
                  (unsigned long)*(volatile uint64_t *)other_spas[i]);
            return false;
        }
    }
    return true;
}

/* ===================================================================
 * TS-NID-01: VS-stage non-identity (VA != GPA, G-stage identity)
 * =================================================================== */
TEST_REGISTER(test_ts_nid_01_vs_only);
bool test_ts_nid_01_vs_only(void) {
    TEST_BEGIN("TS-NID-01: VS-stage non-identity (VA->GPA), G identity");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t A = (uintptr_t)test_data_area;    /* VA */
    uintptr_t B = (uintptr_t)test_fault_page;   /* GPA == SPA (G identity) */
    uintptr_t C = (uintptr_t)test_exec_page;
    uintptr_t D = (uintptr_t)test_exec_target;

    g5_clear4(A, B, C, D);

    two_stage_ctx_t ctx;
    ts2_setup_non_identity(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE,
                           A, B, B,
                           VS_FLAGS_RWX_S_AD, G_FLAGS_RWXU_AD);

    uintptr_t others[] = { A, C, D };
    bool ok = g5_write_and_check(&ctx, A, B, others, 3);
    TEST_ASSERT("VS-stage redirect VA->GPA, write lands at SPA(=GPA)", ok);

    HYP_TEST_END();
}

/* ===================================================================
 * TS-NID-02: G-stage non-identity (VS identity, G GPA->SPA)
 * =================================================================== */
TEST_REGISTER(test_ts_nid_02_g_only);
bool test_ts_nid_02_g_only(void) {
    TEST_BEGIN("TS-NID-02: G-stage non-identity (GPA->SPA), VS identity");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t A = (uintptr_t)test_data_area;    /* VA == GPA */
    uintptr_t B = (uintptr_t)test_fault_page;   /* SPA */
    uintptr_t C = (uintptr_t)test_exec_page;
    uintptr_t D = (uintptr_t)test_exec_target;

    g5_clear4(A, B, C, D);

    two_stage_ctx_t ctx;
    ts2_setup_non_identity(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE,
                           A, A, B,
                           VS_FLAGS_RWX_S_AD, G_FLAGS_RWXU_AD);

    uintptr_t others[] = { A, C, D };
    bool ok = g5_write_and_check(&ctx, A, B, others, 3);
    TEST_ASSERT("G-stage redirect GPA->SPA, write lands at SPA only", ok);

    HYP_TEST_END();
}

/* ===================================================================
 * TS-NID-03: Both stages non-identity (VA -> GPA -> SPA, all distinct)
 * =================================================================== */
TEST_REGISTER(test_ts_nid_03_both);
bool test_ts_nid_03_both(void) {
    TEST_BEGIN("TS-NID-03: VS-stage and G-stage both non-identity");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t A = (uintptr_t)test_data_area;    /* VA */
    uintptr_t B = (uintptr_t)test_fault_page;   /* GPA */
    uintptr_t C = (uintptr_t)test_exec_page;    /* SPA */
    uintptr_t D = (uintptr_t)test_exec_target;

    g5_clear4(A, B, C, D);

    two_stage_ctx_t ctx;
    ts2_setup_non_identity(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE,
                           A, B, C,
                           VS_FLAGS_RWX_S_AD, G_FLAGS_RWXU_AD);

    uintptr_t others[] = { A, B, D };
    bool ok = g5_write_and_check(&ctx, A, C, others, 3);
    TEST_ASSERT("dual redirect VA(A)->GPA(B)->SPA(C), only C modified", ok);

    HYP_TEST_END();
}

/* ===================================================================
 * TS-NID-04: Multi-page non-identity continuity
 *
 * Build VS-stage redirects for 4 distinct VAs to 4 distinct SPAs (G
 * identity). Issue 4 separate VS-mode writes (one per VA) and verify
 * each write lands at its own SPA without disturbing the others.
 *
 * To exercise 4 different magic values we use file-scope payload
 * trampolines so each VS-mode helper writes a distinct constant; the
 * existing test_vs_store always writes HYP_TEST_MAGIC, which would
 * make multi-page isolation indistinguishable.
 * =================================================================== */
static uintptr_t g5_store_m0(uintptr_t a) { *(volatile uint64_t *)a = G5_MAGIC_0; return 0; }
static uintptr_t g5_store_m1(uintptr_t a) { *(volatile uint64_t *)a = G5_MAGIC_1; return 0; }
static uintptr_t g5_store_m2(uintptr_t a) { *(volatile uint64_t *)a = G5_MAGIC_2; return 0; }
static uintptr_t g5_store_m3(uintptr_t a) { *(volatile uint64_t *)a = G5_MAGIC_3; return 0; }

TEST_REGISTER(test_ts_nid_04_multi_page);
bool test_ts_nid_04_multi_page(void) {
    TEST_BEGIN("TS-NID-04: 4-page non-identity, per-page data isolation");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    /* VAs: the 4 named test pages. */
    uintptr_t A = (uintptr_t)test_data_area;
    uintptr_t B = (uintptr_t)test_fault_page;
    uintptr_t C = (uintptr_t)test_exec_page;
    uintptr_t D = (uintptr_t)test_exec_target;

    /* SPAs: the 4 scratch pages following the named ones. They live
     * inside .vm_test_region so they are already covered by G-stage
     * identity built by ts2_setup_full. */
    uintptr_t S0 = (uintptr_t)__vm_test_region_start + 4 * PAGE_SIZE_4K;
    uintptr_t S1 = (uintptr_t)__vm_test_region_start + 5 * PAGE_SIZE_4K;
    uintptr_t S2 = (uintptr_t)__vm_test_region_start + 6 * PAGE_SIZE_4K;
    uintptr_t S3 = (uintptr_t)__vm_test_region_start + 7 * PAGE_SIZE_4K;

    /* Pre-clear all 8 candidate SPAs so any spurious write is detected. */
    g5_clear4(A, B, C, D);
    g5_clear4(S0, S1, S2, S3);

    two_stage_ctx_t ctx;
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    /* VS redirect each VA to its dedicated SPA (G identity covers SPAs). */
    g5_redirect_vs(&ctx, A, S0);
    g5_redirect_vs(&ctx, B, S1);
    g5_redirect_vs(&ctx, C, S2);
    g5_redirect_vs(&ctx, D, S3);

    /* Issue 4 VS-mode writes with distinct magics. */
    (void)ts2_run_check_no_fault(&ctx, g5_store_m0, A);
    (void)ts2_run_check_no_fault(&ctx, g5_store_m1, B);
    (void)ts2_run_check_no_fault(&ctx, g5_store_m2, C);
    (void)ts2_run_check_no_fault(&ctx, g5_store_m3, D);

    bool ok = (*(volatile uint64_t *)S0 == G5_MAGIC_0) &&
              (*(volatile uint64_t *)S1 == G5_MAGIC_1) &&
              (*(volatile uint64_t *)S2 == G5_MAGIC_2) &&
              (*(volatile uint64_t *)S3 == G5_MAGIC_3);
    if (!ok) {
        LOG_W("S0=0x%lx S1=0x%lx S2=0x%lx S3=0x%lx\n",
              (unsigned long)*(volatile uint64_t *)S0,
              (unsigned long)*(volatile uint64_t *)S1,
              (unsigned long)*(volatile uint64_t *)S2,
              (unsigned long)*(volatile uint64_t *)S3);
    }
    TEST_ASSERT("4 SPAs hold the 4 distinct magics in order", ok);

    /* Ensure source VAs (which are also valid GPAs/SPAs in G identity)
     * were NOT modified by the redirected writes. */
    bool clean = (*(volatile uint64_t *)A == 0) &&
                 (*(volatile uint64_t *)B == 0) &&
                 (*(volatile uint64_t *)C == 0) &&
                 (*(volatile uint64_t *)D == 0);
    TEST_ASSERT("source VAs (A,B,C,D) untouched by redirected writes", clean);

    HYP_TEST_END();
}
