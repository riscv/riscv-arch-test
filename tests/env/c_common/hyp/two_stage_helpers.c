/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * common/hyp/two_stage_helpers.c
 *
 * Implementation of framework-level two-stage test helpers.
 * See two_stage_helpers.h for API documentation.
 * =================================================================== */

#include "two_stage_helpers.h"
#include "test_framework.h"

/* ===================================================================
 * Internal helpers
 * =================================================================== */

/* Map kernel/UART low memory in G-stage at 2MB granularity. */
static void map_g_low_mem(two_stage_ctx_t *ctx)
{
    uintptr_t lo_base = PLATFORM_MEM_BASE & ~(PAGE_SIZE_2M - 1);
    uintptr_t lo_end  = TEST_REGION_BASE & ~(PAGE_SIZE_2M - 1);
    for (uintptr_t a = lo_base; a < lo_end; a += PAGE_SIZE_2M) {
        (void)gpt_map_page(&ctx->g_ctx, a, a,
                           G_FLAGS_RWXU_AD, PT_LEVEL_2M);
    }
    /* Stand-alone UART page if it lies outside the kernel image. */
    uintptr_t uart_pg = PLATFORM_UART0_BASE & ~(PAGE_SIZE_4K - 1);
    if (uart_pg < lo_base || uart_pg >= lo_end) {
        (void)gpt_map_page(&ctx->g_ctx, uart_pg, uart_pg,
                           PTE_V|PTE_R|PTE_W|PTE_U|PTE_A|PTE_D,
                           PT_LEVEL_4K);
    }
}

/* Map kernel/UART low memory in VS-stage at 2MB granularity (no U-bit). */
static void map_vs_low_mem(two_stage_ctx_t *ctx)
{
    uintptr_t lo_base = PLATFORM_MEM_BASE & ~(PAGE_SIZE_2M - 1);
    uintptr_t lo_end  = TEST_REGION_BASE & ~(PAGE_SIZE_2M - 1);
    for (uintptr_t a = lo_base; a < lo_end; a += PAGE_SIZE_2M) {
        (void)pt_map_page(&ctx->vs_ctx, a, a,
                          VS_FLAGS_RWX_S_AD, PT_LEVEL_2M);
    }
    uintptr_t uart_pg = PLATFORM_UART0_BASE & ~(PAGE_SIZE_4K - 1);
    if (uart_pg < lo_base || uart_pg >= lo_end) {
        (void)pt_map_page(&ctx->vs_ctx, uart_pg, uart_pg,
                          PTE_V|PTE_R|PTE_W|PTE_A|PTE_D,
                          PT_LEVEL_4K);
    }
}

/* Like map_vs_low_mem, but with U=1 so VU-mode can fetch/access too. */
static void map_vs_low_mem_u(two_stage_ctx_t *ctx)
{
    uintptr_t lo_base = PLATFORM_MEM_BASE & ~(PAGE_SIZE_2M - 1);
    uintptr_t lo_end  = TEST_REGION_BASE & ~(PAGE_SIZE_2M - 1);
    for (uintptr_t a = lo_base; a < lo_end; a += PAGE_SIZE_2M) {
        (void)pt_map_page(&ctx->vs_ctx, a, a,
                          VS_FLAGS_RWXU_AD, PT_LEVEL_2M);
    }
    uintptr_t uart_pg = PLATFORM_UART0_BASE & ~(PAGE_SIZE_4K - 1);
    if (uart_pg < lo_base || uart_pg >= lo_end) {
        (void)pt_map_page(&ctx->vs_ctx, uart_pg, uart_pg,
                          PTE_V|PTE_R|PTE_W|PTE_U|PTE_A|PTE_D,
                          PT_LEVEL_4K);
    }
}

/* Map test region at 4KB granularity in G-stage, with optional victim
 * override for the page containing @victim_gpa. */
static void map_g_test_region(two_stage_ctx_t *ctx, uintptr_t victim_gpa,
                              uintptr_t victim_flags, bool has_victim)
{
    uintptr_t victim_pg = has_victim ? (victim_gpa & ~(PAGE_SIZE_4K - 1))
                                     : 0;
    for (uintptr_t a = TEST_REGION_BASE;
         a < TEST_REGION_END;
         a += PAGE_SIZE_4K)
    {
        uintptr_t f = (has_victim && a == victim_pg)
                      ? victim_flags : G_FLAGS_RWXU_AD;
        (void)gpt_map_page(&ctx->g_ctx, a, a, f, PT_LEVEL_4K);
    }
}

/* Map test region at 4KB granularity in VS-stage (S-level), with
 * optional victim override for the page containing @victim_va. */
static void map_vs_test_region(two_stage_ctx_t *ctx, uintptr_t victim_va,
                               uintptr_t victim_flags, bool has_victim)
{
    uintptr_t victim_pg = has_victim ? (victim_va & ~(PAGE_SIZE_4K - 1))
                                     : 0;
    for (uintptr_t a = TEST_REGION_BASE;
         a < TEST_REGION_END;
         a += PAGE_SIZE_4K)
    {
        uintptr_t f = (has_victim && a == victim_pg)
                      ? victim_flags : VS_FLAGS_RWX_S_AD;
        (void)pt_map_page(&ctx->vs_ctx, a, a, f, PT_LEVEL_4K);
    }
}

/* Map test region at 4KB granularity in VS-stage with a custom default
 * leaf-flag value, with optional victim override for the page
 * containing @victim_va. */
static void map_vs_test_region_flags(two_stage_ctx_t *ctx,
                                     uintptr_t victim_va,
                                     uintptr_t victim_flags, bool has_victim,
                                     uintptr_t default_flags)
{
    uintptr_t victim_pg = has_victim ? (victim_va & ~(PAGE_SIZE_4K - 1))
                                     : 0;
    for (uintptr_t a = TEST_REGION_BASE;
         a < TEST_REGION_END;
         a += PAGE_SIZE_4K)
    {
        uintptr_t f = (has_victim && a == victim_pg)
                      ? victim_flags : default_flags;
        (void)pt_map_page(&ctx->vs_ctx, a, a, f, PT_LEVEL_4K);
    }
}

/* ===================================================================
 * Public foundation helpers
 * =================================================================== */

void ts2_setup_full(two_stage_ctx_t *ctx, int vs_mode, int g_mode)
{
    gpt_pool_reset();
    if (vs_mode != SATP_MODE_BARE) {
        pt_pool_reset();
    }
    two_stage_init(ctx, vs_mode, g_mode);

    if (g_mode != HGATP_MODE_BARE) {
        map_g_low_mem(ctx);
        map_g_test_region(ctx, 0, 0, false);
    }
    if (vs_mode != SATP_MODE_BARE) {
        map_vs_low_mem(ctx);
        map_vs_test_region(ctx, 0, 0, false);
    }
}

void ts2_setup_full_u(two_stage_ctx_t *ctx, int vs_mode, int g_mode)
{
    gpt_pool_reset();
    if (vs_mode != SATP_MODE_BARE) {
        pt_pool_reset();
    }
    two_stage_init(ctx, vs_mode, g_mode);

    if (g_mode != HGATP_MODE_BARE) {
        map_g_low_mem(ctx);
        map_g_test_region(ctx, 0, 0, false);
    }
    if (vs_mode != SATP_MODE_BARE) {
        map_vs_low_mem_u(ctx);
        map_vs_test_region_flags(ctx, 0, 0, false, VS_FLAGS_RWXU_AD);
    }
}

void ts2_setup_with_g_victim(two_stage_ctx_t *ctx, int vs_mode, int g_mode,
                             uintptr_t victim_gpa, uintptr_t victim_g_flags)
{
    gpt_pool_reset();
    if (vs_mode != SATP_MODE_BARE) {
        pt_pool_reset();
    }
    two_stage_init(ctx, vs_mode, g_mode);

    if (g_mode != HGATP_MODE_BARE) {
        map_g_low_mem(ctx);
        map_g_test_region(ctx, victim_gpa, victim_g_flags, true);
    }
    if (vs_mode != SATP_MODE_BARE) {
        map_vs_low_mem(ctx);
        map_vs_test_region(ctx, 0, 0, false);
    }
}

void ts2_setup_with_vs_victim(two_stage_ctx_t *ctx, int vs_mode, int g_mode,
                              uintptr_t victim_va, uintptr_t victim_vs_flags)
{
    gpt_pool_reset();
    pt_pool_reset();
    two_stage_init(ctx, vs_mode, g_mode);

    if (g_mode != HGATP_MODE_BARE) {
        map_g_low_mem(ctx);
        map_g_test_region(ctx, 0, 0, false);
    }
    /* VS victim requires non-Bare VS-stage. */
    map_vs_low_mem(ctx);
    map_vs_test_region(ctx, victim_va, victim_vs_flags, true);
}

void ts2_setup_with_dual_victim(two_stage_ctx_t *ctx, int vs_mode, int g_mode,
                                uintptr_t victim_va,
                                uintptr_t victim_vs_flags,
                                uintptr_t victim_g_flags)
{
    gpt_pool_reset();
    pt_pool_reset();
    two_stage_init(ctx, vs_mode, g_mode);

    if (g_mode != HGATP_MODE_BARE) {
        map_g_low_mem(ctx);
        map_g_test_region(ctx, victim_va, victim_g_flags, true);
    }
    map_vs_low_mem(ctx);
    map_vs_test_region(ctx, victim_va, victim_vs_flags, true);
}

void ts2_setup_non_identity(two_stage_ctx_t *ctx, int vs_mode, int g_mode,
                            uintptr_t va, uintptr_t gpa, uintptr_t spa,
                            uintptr_t vs_flags, uintptr_t g_flags)
{
    gpt_pool_reset();
    if (vs_mode != SATP_MODE_BARE) {
        pt_pool_reset();
    }
    two_stage_init(ctx, vs_mode, g_mode);

    /* Build the canonical identity coverage first. */
    if (g_mode != HGATP_MODE_BARE) {
        map_g_low_mem(ctx);
        map_g_test_region(ctx, 0, 0, false);
    }
    if (vs_mode != SATP_MODE_BARE) {
        map_vs_low_mem(ctx);
        map_vs_test_region(ctx, 0, 0, false);
    }

    /* Now redirect:
     *   VS-stage @va -> @gpa  (only if non-Bare)
     *   G-stage  @gpa -> @spa (only if non-Bare and gpa != spa)
     * The G-stage identity for @gpa is overwritten below; the page at
     * @va is overwritten on the VS-stage side.
     */
    if (vs_mode != SATP_MODE_BARE) {
        /* Re-program the leaf PTE for @va to point at @gpa. The
         * identity entry is overwritten in place. */
        uintptr_t va_pg  = va  & ~(PAGE_SIZE_4K - 1);
        uintptr_t gpa_pg = gpa & ~(PAGE_SIZE_4K - 1);
        uintptr_t *pte = pt_get_pte(&ctx->vs_ctx, va_pg, PT_LEVEL_4K);
        if (pte != NULL) {
            *pte = ((gpa_pg >> 12) << 10) | vs_flags;
        }
    }
    if (g_mode != HGATP_MODE_BARE) {
        uintptr_t gpa_pg = gpa & ~(PAGE_SIZE_4K - 1);
        uintptr_t spa_pg = spa & ~(PAGE_SIZE_4K - 1);
        uintptr_t *pte = gpt_get_pte(&ctx->g_ctx, gpa_pg, PT_LEVEL_4K);
        if (pte != NULL) {
            *pte = ((spa_pg >> 12) << 10) | g_flags;
        }
    }
}

uintptr_t ts2_invalidate_vs_pt_in_g(two_stage_ctx_t *ctx, uintptr_t va,
                                    int target_level)
{
    if (ctx->vs_mode == SATP_MODE_BARE) return 0;
    uintptr_t pt_gpa = two_stage_vs_pt_page_addr(ctx, va, target_level);
    if (pt_gpa == 0) return 0;
    /* Mark the VS-stage PT page invalid in G-stage. The framework
     * helper handles superpage splitting transparently. */
    uintptr_t pt_pg = pt_gpa & ~(PAGE_SIZE_4K - 1);
    ts2_g_override_4k(ctx, pt_pg, 0);
    return pt_pg;
}

/* Internal: split a 2MB G-stage superpage covering @gpa into 512 4KB
 * leaves preserving the original PPN/flags. No-op if already 4K. */
static void g_split_2m_to_4k(gpt_context_t *gctx, uintptr_t gpa) {
    uintptr_t gpa_pg = gpa & ~(PAGE_SIZE_4K - 1);
    /* If a 4K leaf already exists, nothing to split. */
    if (gpt_get_pte(gctx, gpa_pg, PT_LEVEL_4K) != NULL) return;

    uintptr_t *pte_2m = gpt_get_pte(gctx, gpa_pg, PT_LEVEL_2M);
    if (pte_2m == NULL || !PTE_IS_LEAF(*pte_2m)) return;

    uintptr_t flags = (*pte_2m) & ((1UL << 10) - 1UL);
    uintptr_t spa_2m_base = (((*pte_2m) >> 10) << 12) & ~(PAGE_SIZE_2M - 1);
    uintptr_t base_2m = gpa_pg & ~(PAGE_SIZE_2M - 1);
    *pte_2m = 0;  /* Drop the superpage so gpt_map_page may install a
                   * mid-level PT pointer at this slot. */
    for (uintptr_t off = 0; off < PAGE_SIZE_2M; off += PAGE_SIZE_4K) {
        (void)gpt_map_page(gctx, base_2m + off,
                           spa_2m_base + off, flags, PT_LEVEL_4K);
    }
}

void ts2_g_override_4k(two_stage_ctx_t *ctx, uintptr_t gpa, uintptr_t flags) {
    uintptr_t gpa_pg = gpa & ~(PAGE_SIZE_4K - 1);
    /* Ensure 4K granularity exists at this GPA, splitting any 2MB
     * superpage that covers it. */
    g_split_2m_to_4k(&ctx->g_ctx, gpa_pg);
    uintptr_t *pte = gpt_get_pte(&ctx->g_ctx, gpa_pg, PT_LEVEL_4K);
    if (pte != NULL) {
        /* Preserve the original SPA PPN bits; only the flags change. */
        uintptr_t ppn_bits = (*pte) & ~((1UL << 10) - 1UL);
        if (ppn_bits == 0) {
            /* No prior leaf at this 4K slot: install identity mapping. */
            ppn_bits = (gpa_pg >> 12) << 10;
        }
        *pte = ppn_bits | flags;
    } else {
        /* No mid-level PT yet either: install a fresh 4K leaf. */
        (void)gpt_map_page(&ctx->g_ctx, gpa_pg, gpa_pg, flags, PT_LEVEL_4K);
    }
    /* Flush translation caches so the new G-stage mapping (and the
     * implicit-PT-walk associations cached in VS-stage entries) take
     * effect immediately. Without this the prior 2MB superpage in
     * G-stage TLB shadows the freshly installed 4K leaf. */
    hfence_gvma_all();
    hfence_vvma_all();
}

/* ===================================================================
 * Run-and-check helpers
 * =================================================================== */

bool ts2_run_check_fault(two_stage_ctx_t *ctx,
                         uintptr_t (*fn)(uintptr_t), uintptr_t arg,
                         uintptr_t expected_cause)
{
    trap_expect_begin();
    (void)two_stage_run_in_vs(ctx, fn, arg);
    bool fired = trap_was_triggered();
    uintptr_t cause = fired ? trap_get_cause() : 0;
    trap_expect_end();

    /* Cleanup before returning so subsequent assertions in the
     * caller execute under a clean hypervisor state. */
    two_stage_cleanup(ctx);
    hyp_reset_state();

    if (!fired) {
        LOG_E("expected fault (cause=%lu) but none fired\n",
              (unsigned long)expected_cause);
        return false;
    }
    if (cause != expected_cause) {
        LOG_E("cause mismatch: got %lu, expected %lu\n",
              (unsigned long)cause, (unsigned long)expected_cause);
        return false;
    }
    return true;
}

uintptr_t ts2_run_check_no_fault(two_stage_ctx_t *ctx,
                                 uintptr_t (*fn)(uintptr_t),
                                 uintptr_t arg)
{
    trap_expect_begin();
    uintptr_t result = two_stage_run_in_vs(ctx, fn, arg);
    bool fired = trap_was_triggered();
    if (fired) {
        LOG_E("unexpected trap, cause=%lu\n",
              (unsigned long)trap_get_cause());
        result = 0;
    }
    trap_expect_end();
    return result;
}

void ts2_finish(two_stage_ctx_t *ctx)
{
    two_stage_cleanup(ctx);
    hyp_reset_state();
    gpt_pool_reset();
    if (ctx->vs_mode != SATP_MODE_BARE) {
        pt_pool_reset();
    }
}

/* ===================================================================
 * Granularity-aware mapping helpers
 * =================================================================== */

void ts2_map_low_mem_both(two_stage_ctx_t *ctx)
{
    /* G-stage */
    map_g_low_mem(ctx);
    /* VS-stage */
    if (ctx->vs_mode != SATP_MODE_BARE) {
        map_vs_low_mem(ctx);
    }
}

void ts2_map_low_mem_g(two_stage_ctx_t *ctx)
{
    map_g_low_mem(ctx);
}

void ts2_map_low_mem_vs(two_stage_ctx_t *ctx)
{
    map_vs_low_mem(ctx);
}

void ts2_map_region_g(two_stage_ctx_t *ctx, int level)
{
    if (level >= PT_LEVEL_512G) {
        /* 512G/256T superpage: anchor it to the superpage-aligned base of
         * the test region rather than GPA=0. On high-MEM_BASE platforms
         * (e.g. NGF-C9502, MEM_BASE=0x800008000000 ~128TB) a superpage at
         * GPA=0 only covers [0, size) and misses the test region entirely,
         * causing a load/store guest-page-fault. Aligning to the region base
         * keeps behavior identical on low-MEM_BASE platforms (base==0). */
        uintptr_t sz   = PAGE_SIZE_AT_LEVEL(level);
        uintptr_t base = TEST_REGION_BASE & ~(sz - 1);
        (void)gpt_map_page(&ctx->g_ctx, base, base, G_FLAGS_RWXU_AD, level);
        /* The UART may live far below the test region and thus outside
         * this superpage; map it separately so console output still works
         * when the caller relies on a single large page (no low-mem map). */
        uintptr_t uart_pg = PLATFORM_UART0_BASE & ~(PAGE_SIZE_4K - 1);
        if (uart_pg < base || uart_pg >= base + sz) {
            (void)gpt_map_page(&ctx->g_ctx, uart_pg, uart_pg,
                               PTE_V|PTE_R|PTE_W|PTE_U|PTE_A|PTE_D,
                               PT_LEVEL_4K);
        }
    } else if (level == PT_LEVEL_1G) {
        uintptr_t base1g = TEST_REGION_BASE & ~(PAGE_SIZE_1G - 1);
        (void)gpt_map_page(&ctx->g_ctx, base1g, base1g,
                           G_FLAGS_RWXU_AD, PT_LEVEL_1G);
    } else if (level == PT_LEVEL_2M) {
        for (uintptr_t a = TEST_REGION_BASE; a < TEST_REGION_END;
             a += PAGE_SIZE_2M) {
            (void)gpt_map_page(&ctx->g_ctx, a, a,
                               G_FLAGS_RWXU_AD, PT_LEVEL_2M);
        }
    } else { /* 4K */
        for (uintptr_t a = TEST_REGION_BASE; a < TEST_REGION_END;
             a += PAGE_SIZE_4K) {
            (void)gpt_map_page(&ctx->g_ctx, a, a,
                               G_FLAGS_RWXU_AD, PT_LEVEL_4K);
        }
    }
}

void ts2_map_region_vs(two_stage_ctx_t *ctx, int level)
{
    if (level >= PT_LEVEL_512G) {
        /* 512G/256T superpage: anchor to the superpage-aligned base of the
         * test region (VA==GPA identity) instead of VA=0. See the matching
         * comment in ts2_map_region_g(): a VA=0 superpage misses the region
         * on high-MEM_BASE platforms. base==0 on low-MEM_BASE platforms. */
        uintptr_t sz   = PAGE_SIZE_AT_LEVEL(level);
        uintptr_t base = TEST_REGION_BASE & ~(sz - 1);
        (void)pt_map_page(&ctx->vs_ctx, base, base, VS_FLAGS_RWX_S_AD, level);
        /* Map the UART page separately when it falls outside the superpage. */
        uintptr_t uart_pg = PLATFORM_UART0_BASE & ~(PAGE_SIZE_4K - 1);
        if (uart_pg < base || uart_pg >= base + sz) {
            (void)pt_map_page(&ctx->vs_ctx, uart_pg, uart_pg,
                              PTE_V|PTE_R|PTE_W|PTE_A|PTE_D, PT_LEVEL_4K);
        }
    } else if (level == PT_LEVEL_1G) {
        uintptr_t base1g = TEST_REGION_BASE & ~(PAGE_SIZE_1G - 1);
        (void)pt_map_page(&ctx->vs_ctx, base1g, base1g,
                          VS_FLAGS_RWX_S_AD, PT_LEVEL_1G);
    } else if (level == PT_LEVEL_2M) {
        for (uintptr_t a = TEST_REGION_BASE; a < TEST_REGION_END;
             a += PAGE_SIZE_2M) {
            (void)pt_map_page(&ctx->vs_ctx, a, a,
                              VS_FLAGS_RWX_S_AD, PT_LEVEL_2M);
        }
    } else { /* 4K */
        for (uintptr_t a = TEST_REGION_BASE; a < TEST_REGION_END;
             a += PAGE_SIZE_4K) {
            (void)pt_map_page(&ctx->vs_ctx, a, a,
                              VS_FLAGS_RWX_S_AD, PT_LEVEL_4K);
        }
    }
}

void ts2_setup_granular(two_stage_ctx_t *ctx, int vs_mode, int g_mode,
                        int vs_level, int g_level)
{
    gpt_pool_reset();
    if (vs_mode != SATP_MODE_BARE) {
        pt_pool_reset();
    }
    two_stage_init(ctx, vs_mode, g_mode);

    if (g_mode != HGATP_MODE_BARE) {
        map_g_low_mem(ctx);
        ts2_map_region_g(ctx, g_level);
    }
    if (vs_mode != SATP_MODE_BARE) {
        map_vs_low_mem(ctx);
        ts2_map_region_vs(ctx, vs_level);
    }
}

/* ===================================================================
 * henvcfg field control helpers
 * =================================================================== */

void ts2_enable_adue(void)
{
    uintptr_t mv = tsbi_csr_read(CSR_MENVCFG);
    tsbi_csr_write(CSR_MENVCFG, mv | MENVCFG_ADUE);
    henvcfg_set_adue(true);
}

void ts2_disable_adue(void)
{
    henvcfg_set_adue(false);
    uintptr_t mv = tsbi_csr_read(CSR_MENVCFG);
    tsbi_csr_write(CSR_MENVCFG, mv & ~MENVCFG_ADUE);
}

void ts2_enable_pbmte(void)
{
    uintptr_t mv = tsbi_csr_read(CSR_MENVCFG);
    tsbi_csr_write(CSR_MENVCFG, mv | MENVCFG_PBMTE);
    henvcfg_set_pbmte(true);
}

void ts2_disable_pbmte(void)
{
    henvcfg_set_pbmte(false);
    uintptr_t mv = tsbi_csr_read(CSR_MENVCFG);
    tsbi_csr_write(CSR_MENVCFG, mv & ~MENVCFG_PBMTE);
}
