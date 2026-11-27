/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * hyp_test_helpers_region.c - G-stage fault helpers that depend on
 * the __vm_test_region_start/__vm_test_region_end linker region.
 *
 * Only suites whose kernel.ld provides the .vm_test_region section
 * may link this object; keep it out of COMMON_OBJS and add it to
 * EXT_OBJS per suite.
 * =================================================================== */

#include "hyp_test_helpers.h"
#include "two_stage_helpers.h"   /* SUITE_HGATP_MODE / SUITE_VSATP_MODE fallback */

/* ===================================================================
 * G-stage fault helpers.
 * =================================================================== */

void setup_gstage_with_victim(two_stage_ctx_t *ctx,
                              uintptr_t victim_gpa,
                              uintptr_t victim_flags)
{
    gpt_pool_reset();
    two_stage_init(ctx, SATP_MODE_BARE, SUITE_HGATP_MODE);

    /* Kernel/UART at 2MB. */
    uintptr_t lo_base = PLATFORM_MEM_BASE & ~(PAGE_SIZE_2M - 1);
    uintptr_t lo_end  = (uintptr_t)__vm_test_region_start
                        & ~(PAGE_SIZE_2M - 1);
    two_stage_setup_identity(ctx, lo_base, lo_end - lo_base,
                             G_FLAGS_RWXU_AD, PT_LEVEL_2M);

    /* Test region at 4KB. */
    uintptr_t r_start = (uintptr_t)__vm_test_region_start;
    uintptr_t r_size  = (uintptr_t)__vm_test_region_end - r_start;
    two_stage_setup_identity(ctx, r_start, r_size,
                             G_FLAGS_RWXU_AD, PT_LEVEL_4K);

    /* Override victim page flags. */
    uintptr_t victim_page = victim_gpa & ~(PAGE_SIZE_4K - 1);
    two_stage_g_map_page(ctx, victim_page, victim_page,
                         victim_flags, PT_LEVEL_4K);
}

bool fire_vs_load_fault(uintptr_t victim_gpa, uintptr_t flags) {
    two_stage_ctx_t ctx;
    setup_gstage_with_victim(&ctx, victim_gpa, flags);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_load_expect_fault, victim_gpa);
    bool fired = trap_was_triggered();
    trap_expect_end();

    two_stage_cleanup(&ctx);
    return fired;
}

bool fire_vs_store_fault(uintptr_t victim_gpa, uintptr_t flags) {
    two_stage_ctx_t ctx;
    setup_gstage_with_victim(&ctx, victim_gpa, flags);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_store_expect_fault, victim_gpa);
    bool fired = trap_was_triggered();
    trap_expect_end();

    two_stage_cleanup(&ctx);
    return fired;
}

bool probe_load_gpf(uintptr_t victim_gpa, uintptr_t victim_flags) {
    two_stage_ctx_t ctx;
    setup_gstage_with_victim(&ctx, victim_gpa, victim_flags);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, vs_load_probe, victim_gpa);
    bool fired = trap_was_triggered();
    trap_expect_end();

    two_stage_cleanup(&ctx);
    return fired;
}

bool probe_store_gpf(uintptr_t victim_gpa, uintptr_t victim_flags) {
    two_stage_ctx_t ctx;
    setup_gstage_with_victim(&ctx, victim_gpa, victim_flags);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, vs_store_probe, victim_gpa);
    bool fired = trap_was_triggered();
    trap_expect_end();

    two_stage_cleanup(&ctx);
    return fired;
}

/* Compressed-load variant (TINST-08): same GPF scenario but the
 * trapping instruction is a 2-byte `c.lw`. */
bool probe_load_gpf_c(uintptr_t victim_gpa, uintptr_t victim_flags) {
    two_stage_ctx_t ctx;
    setup_gstage_with_victim(&ctx, victim_gpa, victim_flags);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, vs_load_probe_c, victim_gpa);
    bool fired = trap_was_triggered();
    trap_expect_end();

    two_stage_cleanup(&ctx);
    return fired;
}

uintptr_t setup_implicit_walk_victim(two_stage_ctx_t *ctx,
                                     uintptr_t test_va,
                                     uintptr_t victim_g_flags)
{
    return setup_implicit_walk_victim_level(ctx, test_va, PT_LEVEL_4K,
                                            victim_g_flags);
}

uintptr_t setup_implicit_walk_victim_level(two_stage_ctx_t *ctx,
                                           uintptr_t test_va,
                                           int victim_pt_level,
                                           uintptr_t victim_g_flags)
{
    gpt_pool_reset();
    two_stage_init(ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    /* --- VS-stage: identity-map the kernel/low region at 2MB and
     *     map test_va into the test region at 4KB (creates the leaf
     *     PT page that becomes the implicit-access victim). --- */
    uintptr_t lo_base  = PLATFORM_MEM_BASE & ~(PAGE_SIZE_2M - 1);
    uintptr_t r_start  = (uintptr_t)__vm_test_region_start;
    uintptr_t lo_end   = r_start & ~(PAGE_SIZE_2M - 1);
    uintptr_t vs_flags = PTE_V | PTE_R | PTE_W | PTE_X | PTE_A | PTE_D;

    two_stage_vs_identity(ctx, lo_base, lo_end - lo_base,
                          vs_flags, PT_LEVEL_2M);
    two_stage_vs_map(ctx, test_va, r_start, vs_flags, PT_LEVEL_4K);

    /* PT page holding the PTE for test_va at the requested level. */
    uintptr_t victim_gpa =
        two_stage_vs_pt_page_addr(ctx, test_va, victim_pt_level);
    if (victim_gpa == 0)
        return 0;
    uintptr_t victim_page = victim_gpa & ~(PAGE_SIZE_4K - 1);

    /* --- G-stage: 4KB identity over kernel + test region so the
     *     single victim PT page can be overridden. --- */
    two_stage_setup_identity(ctx, lo_base, r_start - lo_base,
                             G_FLAGS_RWXU_AD, PT_LEVEL_4K);
    uintptr_t r_end = (uintptr_t)__vm_test_region_end;
    two_stage_setup_identity(ctx, r_start, r_end - r_start,
                             G_FLAGS_RWXU_AD, PT_LEVEL_4K);

    two_stage_g_map_page(ctx, victim_page, victim_page,
                         victim_g_flags, PT_LEVEL_4K);

    return victim_gpa;
}
