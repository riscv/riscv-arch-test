/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * common/hyp/two_stage.c — Two-stage translation orchestration
 * =================================================================== */

#include "two_stage.h"
#include "hyp_priv.h"
#include "hyp_csr.h"
#include "test_framework.h"

void two_stage_init(two_stage_ctx_t *ctx, int vs_mode, int g_mode) {
    ctx->vs_mode = vs_mode;
    if (vs_mode == SATP_MODE_BARE) {
        ctx->vs_ctx.root_pt = NULL;
        ctx->vs_ctx.mode = SATP_MODE_BARE;
    } else {
        pt_pool_reset();
        pt_init(&ctx->vs_ctx, vs_mode);
    }
    if (g_mode == HGATP_MODE_BARE) {
        /* G-stage disabled: leave gpt_context unallocated. The
         * framework helpers and gpt_enable() must honor BARE and
         * skip page-table programming. */
        ctx->g_ctx.root_pt = NULL;
        ctx->g_ctx.mode    = HGATP_MODE_BARE;
        ctx->g_ctx.levels  = 0;
    } else {
        gpt_init(&ctx->g_ctx, g_mode);
    }
}

int two_stage_setup_identity(two_stage_ctx_t *ctx, uintptr_t base,
                             uintptr_t size, uintptr_t flags, int level) {
    return gpt_setup_identity_mapping(&ctx->g_ctx, base, size, flags, level);
}

int two_stage_g_map_page(two_stage_ctx_t *ctx, uintptr_t gpa,
                         uintptr_t spa, uintptr_t flags, int level) {
    return gpt_map_page(&ctx->g_ctx, gpa, spa, flags, level);
}

void two_stage_enable(two_stage_ctx_t *ctx, unsigned vmid) {
    /* World-switch sequence per RISC-V spec:
     *   1. vsatp = 0  (neutralize old VS-stage)
     *   2. hgatp = new (activate G-stage)
     *   3. vsatp = new (activate VS-stage, if non-Bare)
     *   4. HFENCE.VVMA (flush stale VS-stage TLB entries) */
    CSRW(CSR_VSATP, 0);
    gpt_enable(&ctx->g_ctx, vmid);

    if (ctx->vs_mode != SATP_MODE_BARE) {
        uintptr_t root_ppn = ((uintptr_t)ctx->vs_ctx.root_pt) >> PAGE_SHIFT;
        uintptr_t vsatp = MAKE_SATP(ctx->vs_ctx.mode, 0, root_ppn);
        CSRW(CSR_VSATP, vsatp);
    }

    /* HFENCE.VVMA must follow *any* vsatp change, including the Bare
     * case (vsatp=0) written above.  Without it, VS-stage TLB entries
     * cached by an earlier paged vsatp (e.g. a prior Sv39/48/57 VS
     * test) survive and get reused for the next VS-mode instruction
     * fetch, translating the payload PC to a stale GPA that the current
     * G-stage does not map -> an instruction guest-page-fault on real
     * hardware.  Simulators that do not model VS-stage TLB staleness
     * mask this.  gpt_enable() already issued HFENCE.GVMA for hgatp. */
    hfence_vvma_all();
}

uintptr_t two_stage_run_in_vs(two_stage_ctx_t *ctx,
                              uintptr_t (*fn)(uintptr_t),
                              uintptr_t arg)
{
    two_stage_enable(ctx, /*vmid=*/0);
    return run_in_vs_mode(fn, arg);
}

uintptr_t two_stage_run_in_vu(two_stage_ctx_t *ctx,
                              uintptr_t (*fn)(uintptr_t),
                              uintptr_t arg)
{
    two_stage_enable(ctx, /*vmid=*/0);
    return run_in_vu_mode(fn, arg);
}

void two_stage_cleanup(two_stage_ctx_t *ctx) {
    gpt_disable();
    CSRW(CSR_VSATP, 0);
    /* Flush VS-stage TLB after clearing vsatp so this context's
     * VS-stage entries cannot leak into a later VS-mode run (mirrors
     * the HFENCE.VVMA in two_stage_enable).  gpt_disable() already
     * issued HFENCE.GVMA. */
    hfence_vvma_all();
    ctx->g_ctx.root_pt = NULL;
    if (ctx->vs_mode != SATP_MODE_BARE) {
        ctx->vs_ctx.root_pt = NULL;
    }
}

/* ===================================================================
 * VS-stage page table helpers
 * =================================================================== */

int two_stage_vs_map(two_stage_ctx_t *ctx, uintptr_t va,
                     uintptr_t gpa, uintptr_t flags, int level) {
    if (ctx->vs_mode == SATP_MODE_BARE) {
        LOG_E("two_stage_vs_map: vs_mode is BARE\n");
        return -1;
    }
    return pt_map_page(&ctx->vs_ctx, va, gpa, flags, level);
}

int two_stage_vs_identity(two_stage_ctx_t *ctx, uintptr_t base,
                          uintptr_t size, uintptr_t flags, int level) {
    if (ctx->vs_mode == SATP_MODE_BARE) {
        LOG_E("two_stage_vs_identity: vs_mode is BARE\n");
        return -1;
    }
    return pt_setup_identity_mapping(&ctx->vs_ctx, base, size, flags, level);
}

uintptr_t two_stage_vs_pt_page_addr(two_stage_ctx_t *ctx,
                                    uintptr_t va, int target_level) {
    if (ctx->vs_mode == SATP_MODE_BARE)
        return 0;
    return get_pt_page_addr(&ctx->vs_ctx, va, target_level);
}
