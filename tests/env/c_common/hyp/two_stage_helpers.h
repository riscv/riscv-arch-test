/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef TWO_STAGE_HELPERS_H
#define TWO_STAGE_HELPERS_H

/* ===================================================================
 * common/hyp/two_stage_helpers.h
 *
 * Framework-level helpers for two-stage (VS-stage + G-stage) test
 * scenarios. These are the centralized building blocks used by all
 * Group tests in `common/hyp/tests_2stage/`. They subsume the
 * per-suite `test_helpers.{h,c}` so that public logic lives in the
 * framework, not in each test directory.
 *
 * All helpers accept caller-specified vs_mode / g_mode so they can
 * be reused unchanged across the Sv39x4 / Sv48x4 / Sv57x4 suites.
 *
 * Linker-provided symbols required by these helpers (each suite's
 * kernel.ld must export):
 *   __vm_test_region_start / __vm_test_region_end  -- 2MB test region
 *   test_data_area / test_fault_page / test_exec_page / test_exec_target
 * =================================================================== */

#include "test_framework.h"
#include "vm/vm.h"
#include "hyp_defs.h"
#include "hyp_csr.h"
#include "hyp_priv.h"
#include "hyp_reset.h"
#include "hyp_test.h"
#include "hyp_fence.h"
#include "hyp_ldst.h"
#include "gstage_pt.h"
#include "two_stage.h"
#include "test_vs_helpers.h"

/* ----- linker-provided test region symbols (per-suite kernel.ld) ----- */
extern uint8_t __vm_test_region_start[];
extern uint8_t __vm_test_region_end[];
extern uint8_t test_data_area[];
extern uint8_t test_fault_page[];
extern uint8_t test_exec_page[];
extern uint8_t test_exec_target[];

#ifndef TEST_REGION_BASE
#define TEST_REGION_BASE  ((uintptr_t)__vm_test_region_start)
#endif
#ifndef TEST_REGION_END
#define TEST_REGION_END   ((uintptr_t)__vm_test_region_end)
#endif

/* ===================================================================
 * Permission flag presets
 * =================================================================== */

/* G-stage default leaf PTE (G-stage views all accesses as U-mode). */
#ifndef G_FLAGS_RWXU_AD
#define G_FLAGS_RWXU_AD  (PTE_V|PTE_R|PTE_W|PTE_X|PTE_U|PTE_A|PTE_D)
#endif

/* VS-stage default leaf PTE for an S-level (VS-mode) access:
 * U=0 because VS-mode is the "supervisor of the guest". */
#define VS_FLAGS_RWX_S_AD   (PTE_V|PTE_R|PTE_W|PTE_X|PTE_A|PTE_D)

/* VS-stage S-level leaf PTE without execute permission (X=0):
 * instruction fetch from such a page raises an instruction page fault. */
#define VS_FLAGS_RW_S_AD    (PTE_V|PTE_R|PTE_W|PTE_A|PTE_D)

/* VS-stage default leaf PTE for a U-level (VU-mode) access. */
#define VS_FLAGS_RWXU_AD    (PTE_V|PTE_R|PTE_W|PTE_X|PTE_U|PTE_A|PTE_D)

/* ===================================================================
 * Foundation setup helpers
 * =================================================================== */

/**
 * ts2_setup_full - Reset pools, init two-stage ctx, build full identity:
 *   - Kernel/UART low memory at 2MB granularity (G-stage only)
 *   - .vm_test_region pages at 4KB granularity (VS+G stages)
 *
 * After return, M-mode caller may invoke two_stage_run_in_vs() and
 * trampoline into VS-mode without any further setup.
 *
 * vs_mode: SATP_MODE_BARE / SV39 / SV48 / SV57
 * g_mode:  HGATP_MODE_BARE / SV39X4 / SV48X4 / SV57X4
 *
 * Notes:
 * - When vs_mode != BARE, VS-stage identity-maps the test region
 *   with VS_FLAGS_RWX_S_AD (S-level access; safe for run_in_vs_mode).
 * - When g_mode  != BARE, G-stage identity-maps both kernel/UART and
 *   the test region with G_FLAGS_RWXU_AD.
 */
void ts2_setup_full(two_stage_ctx_t *ctx, int vs_mode, int g_mode);

/**
 * ts2_setup_full_u - Like ts2_setup_full, but VS-stage identity-maps
 * the test region with VS_FLAGS_RWXU_AD (U=1), so VU-mode (V=1, U)
 * code can fetch/load/store inside it. The kernel-image and UART
 * mappings stay at S-level (U=0) which is correct because VU-mode
 * never executes from those regions; only the trampoline touches
 * them in VS-mode.
 */
void ts2_setup_full_u(two_stage_ctx_t *ctx, int vs_mode, int g_mode);

/**
 * ts2_setup_with_g_victim - Like ts2_setup_full, but the 4KB G-stage
 * page covering @victim_gpa is overridden with @victim_g_flags.
 *
 * Used to inject a single faulting G-stage page (e.g. V=0, R-only,
 * U=0, A=0) while leaving the rest of the test region accessible.
 */
void ts2_setup_with_g_victim(two_stage_ctx_t *ctx, int vs_mode, int g_mode,
                             uintptr_t victim_gpa, uintptr_t victim_g_flags);

/**
 * ts2_setup_with_vs_victim - Like ts2_setup_full, but the 4KB VS-stage
 * page covering @victim_va is overridden with @victim_vs_flags.
 * Requires vs_mode != BARE.
 */
void ts2_setup_with_vs_victim(two_stage_ctx_t *ctx, int vs_mode, int g_mode,
                              uintptr_t victim_va, uintptr_t victim_vs_flags);

/**
 * ts2_setup_with_dual_victim - Override both VS-stage and G-stage
 * leaf PTEs for the 4KB page covering @victim_va == @victim_gpa.
 * Requires vs_mode != BARE.
 */
void ts2_setup_with_dual_victim(two_stage_ctx_t *ctx, int vs_mode, int g_mode,
                                uintptr_t victim_va,
                                uintptr_t victim_vs_flags,
                                uintptr_t victim_g_flags);

/**
 * ts2_setup_non_identity - Build a non-identity two-stage layout:
 *   VS-stage: @va -> @gpa
 *   G-stage:  @gpa -> @spa
 * Plus full identity coverage of code/UART/test-region everywhere
 * except the GPA range used by the non-identity mapping.
 *
 * Each of va/gpa/spa must be 4KB-aligned and must fall within the
 * test region (so backing storage is available for the SPA).
 */
void ts2_setup_non_identity(two_stage_ctx_t *ctx, int vs_mode, int g_mode,
                            uintptr_t va, uintptr_t gpa, uintptr_t spa,
                            uintptr_t vs_flags, uintptr_t g_flags);

/**
 * ts2_invalidate_vs_pt_in_g - Mark the VS-stage page-table page that
 * resides at the GPA of the PT for @va at @target_level as INVALID
 * in G-stage. Requires vs_mode != BARE and that VS-stage already has
 * an entry at that level (i.e. caller has already mapped @va).
 *
 * Returns the GPA that was made invalid (useful for htval assertions).
 * Returns 0 if the level has no PT page yet.
 */
uintptr_t ts2_invalidate_vs_pt_in_g(two_stage_ctx_t *ctx, uintptr_t va,
                                    int target_level);

/**
 * ts2_g_override_4k - Override the G-stage 4KB leaf for @gpa with the
 * given @flags (use flags=0 to invalidate). When @gpa is currently
 * covered by a 2MB or 1GB superpage, the superpage is split to 4KB
 * leaves first (preserving the original SPA mapping and flags for
 * all neighbour pages).
 */
void ts2_g_override_4k(two_stage_ctx_t *ctx, uintptr_t gpa, uintptr_t flags);

/* ===================================================================
 * Run-and-check helpers
 * =================================================================== */

/**
 * ts2_run_check_fault - Run @fn(@arg) inside VS-mode and assert that
 * a guest-page-fault fires with cause == @expected_cause.
 *
 * Performs cleanup (gpt_disable + vsatp=0 + hyp_reset_state) before
 * returning. Logs diagnostic info on mismatch.
 *
 * Returns true on cause match.
 */
bool ts2_run_check_fault(two_stage_ctx_t *ctx,
                         uintptr_t (*fn)(uintptr_t), uintptr_t arg,
                         uintptr_t expected_cause);

/**
 * ts2_run_check_no_fault - Run @fn(@arg) in VS-mode and assert no
 * trap occurred. Returns the helper's return value (or 0 on trap).
 */
uintptr_t ts2_run_check_no_fault(two_stage_ctx_t *ctx,
                                 uintptr_t (*fn)(uintptr_t),
                                 uintptr_t arg);

/**
 * ts2_finish - Common test-end teardown:
 *   - two_stage_cleanup
 *   - hyp_reset_state
 *   - gpt_pool_reset
 *   - pt_pool_reset (if vs_mode != BARE)
 */
void ts2_finish(two_stage_ctx_t *ctx);

/* ===================================================================
 * Granularity-aware mapping helpers
 *
 * These allow test groups to build two-stage layouts at arbitrary
 * page granularities (4K / 2M / 1G) without duplicating the
 * region-iteration logic.
 * =================================================================== */

/**
 * ts2_map_low_mem_both - Map kernel/UART low memory on BOTH G-stage
 * and VS-stage at 2MB granularity. Equivalent to the internal
 * map_g_low_mem + map_vs_low_mem in ts2_setup_full, but exposed for
 * tests that need custom test-region mappings.
 */
void ts2_map_low_mem_both(two_stage_ctx_t *ctx);

/**
 * ts2_map_low_mem_g - Map kernel/UART low memory on G-stage only
 * at 2MB granularity.
 */
void ts2_map_low_mem_g(two_stage_ctx_t *ctx);

/**
 * ts2_map_low_mem_vs - Map kernel/UART low memory on VS-stage only
 * at 2MB granularity.
 */
void ts2_map_low_mem_vs(two_stage_ctx_t *ctx);

/**
 * ts2_map_region_g - Map the test region in G-stage at the specified
 * level (PT_LEVEL_4K / PT_LEVEL_2M / PT_LEVEL_1G / PT_LEVEL_512G /
 * PT_LEVEL_256T). Uses G_FLAGS_RWXU_AD as the leaf flags.
 * For 512G/256T: maps a single superpage at GPA=0 covering all memory.
 */
void ts2_map_region_g(two_stage_ctx_t *ctx, int level);

/**
 * ts2_map_region_vs - Map the test region in VS-stage at the
 * specified level (4K / 2M / 1G / 512G / 256T).
 * Uses VS_FLAGS_RWX_S_AD.
 * For 512G/256T: maps a single superpage at VA=0 covering all memory.
 */
void ts2_map_region_vs(two_stage_ctx_t *ctx, int level);

/**
 * ts2_setup_granular - Full setup (init + low-mem + test-region)
 * with explicit control over page granularity on both stages.
 *
 * Equivalent to: pool_reset + two_stage_init + map_low_mem_both +
 *   map_region_g(g_level) + map_region_vs(vs_level).
 */
void ts2_setup_granular(two_stage_ctx_t *ctx, int vs_mode, int g_mode,
                        int vs_level, int g_level);

/* ===================================================================
 * Mode-to-level / level-to-page-size helpers
 *
 * These small utilities let granularity-driven test files iterate over
 * legal (vs_level, g_level) combinations without baking mode
 * knowledge into each test file. They are pure helpers and contain no
 * test logic.
 * =================================================================== */

/* Highest legal leaf level for a VS-stage satp mode.
 *   SV39 -> PT_LEVEL_1G  (level 2)
 *   SV48 -> PT_LEVEL_512G (level 3)
 *   SV57 -> PT_LEVEL_256T (level 4)
 *   BARE -> PT_LEVEL_4K  (no walk; placeholder)
 */
static inline int vs_max_level(int vs_mode) {
    switch (vs_mode) {
    case SATP_MODE_SV39: return PT_LEVEL_1G;
    case SATP_MODE_SV48: return PT_LEVEL_512G;
    case SATP_MODE_SV57: return PT_LEVEL_256T;
    default:             return PT_LEVEL_4K;
    }
}

/* Highest legal leaf level for a G-stage hgatp mode.
 *   SV39X4 -> PT_LEVEL_1G
 *   SV48X4 -> PT_LEVEL_512G
 *   SV57X4 -> PT_LEVEL_256T
 *   BARE   -> PT_LEVEL_4K
 */
static inline int g_max_level(int g_mode) {
    switch (g_mode) {
    case HGATP_MODE_SV39X4: return PT_LEVEL_1G;
    case HGATP_MODE_SV48X4: return PT_LEVEL_512G;
    case HGATP_MODE_SV57X4: return PT_LEVEL_256T;
    default:                return PT_LEVEL_4K;
    }
}

/* Page size (in bytes) for a leaf at the given level. */
#define PAGE_SIZE_AT_LEVEL(lv) \
    ((lv) == PT_LEVEL_4K   ? PAGE_SIZE_4K   : \
     (lv) == PT_LEVEL_2M   ? PAGE_SIZE_2M   : \
     (lv) == PT_LEVEL_1G   ? PAGE_SIZE_1G   : \
     (lv) == PT_LEVEL_512G ? (1ULL << 39)   : \
                             (1ULL << 48))

/* ===================================================================
 * henvcfg field control helpers
 * =================================================================== */

/** Enable Svadu: set menvcfg.ADUE=1 then henvcfg.ADUE=1. */
void ts2_enable_adue(void);

/** Disable Svadu: clear henvcfg.ADUE then menvcfg.ADUE. */
void ts2_disable_adue(void);

/** Enable Svpbmt: set menvcfg.PBMTE=1 then henvcfg.PBMTE=1. */
void ts2_enable_pbmte(void);

/** Disable Svpbmt: clear henvcfg.PBMTE then menvcfg.PBMTE. */
void ts2_disable_pbmte(void);

/* ===================================================================
 * MXR / SUM / MPRV+MPV control helpers
 * =================================================================== */

/** Set sstatus.MXR (HS-level). */
static inline void ts2_set_sstatus_mxr(int v) {
    uintptr_t s = CSRR(sstatus);
    if (v) s |= MSTATUS_MXR_BIT; else s &= ~MSTATUS_MXR_BIT;
    CSRW(sstatus, s);
}

/** Set vsstatus.MXR (VS-level). */
static inline void ts2_set_vsstatus_mxr(int v) {
    uintptr_t s = CSRR(CSR_VSSTATUS);
    if (v) s |= MSTATUS_MXR_BIT; else s &= ~MSTATUS_MXR_BIT;
    CSRW(CSR_VSSTATUS, s);
}

/** Set mstatus.MPV and mstatus.MPP for MPRV-based guest loads. */
static inline void ts2_set_mprv_mpv(int mpv, unsigned mpp) {
    uintptr_t m = CSRR(mstatus);
    m &= ~(MSTATUS_MPV | MSTATUS_MPP_MASK | MSTATUS_MPRV_BIT);
    if (mpv) m |= MSTATUS_MPV;
    m |= ((uintptr_t)mpp << MSTATUS_MPP_OFF) & MSTATUS_MPP_MASK;
    m |= MSTATUS_MPRV_BIT;
    CSRW(mstatus, m);
}

/** Clear mstatus.MPRV (disable privilege override). */
static inline void ts2_clear_mprv(void) {
    CSRC(mstatus, MSTATUS_MPRV_BIT);
}

/** M-mode load via MPRV (reads 8 bytes from @addr with current MPP/MPV). */
static inline uint64_t ts2_mprv_load_d(uintptr_t addr) {
    uint64_t val;
#if __riscv_xlen == 64
    asm volatile("ld %0, 0(%1)" : "=r"(val) : "r"(addr) : "memory");
#else
    uint32_t lo, hi;
    asm volatile("lw %0, 0(%2)\n\t"
                 "lw %1, 4(%2)"
                 : "=&r"(lo), "=r"(hi)
                 : "r"(addr) : "memory");
    val = ((uint64_t)hi << 32) | lo;
#endif
    return val;
}

/* ===================================================================
 * Leaf-PTE flag editors (VS-stage and G-stage).
 *
 * Rewrite the permission/attribute bits of the leaf PTE covering @va
 * (VS-stage) or @gpa (G-stage) at @level, preserving the PPN. Used by
 * tests that flip a single page's V/R/W/X/U/A/D after the mapping is
 * already built. No-op when the PTE at that level is not present.
 * =================================================================== */
static inline void vs_pte_modify(two_stage_ctx_t *ctx, uintptr_t va, int level,
                                 uintptr_t new_flags) {
    uintptr_t *pte = pt_get_pte(&ctx->vs_ctx, va, level);
    if (pte) {
        *pte = (*pte & ~(PTE_V|PTE_R|PTE_W|PTE_X|PTE_U|PTE_A|PTE_D)) | new_flags;
    }
}

static inline void g_pte_modify(two_stage_ctx_t *ctx, uintptr_t gpa, int level,
                                uintptr_t new_flags) {
    uintptr_t *pte = gpt_get_pte(&ctx->g_ctx, gpa, level);
    if (pte) {
        *pte = (*pte & ~(PTE_V|PTE_R|PTE_W|PTE_X|PTE_U|PTE_A|PTE_D)) | new_flags;
    }
}

/* ===================================================================
 * Suite default paging modes (G-stage and VS-stage)
 *
 * A mode-intrinsic suite (e.g. Sv39x4) pins SUITE_HGATP_MODE /
 * SUITE_VSATP_MODE to a fixed MODE (via its Makefile -D or an explicit
 * #define) BEFORE including the shared Group test files. A mode-agnostic
 * suite leaves them undefined and gets the platform-selected mode
 * (PLATFORM_HGATP_MODE / PLATFORM_SATP_MODE from capabilities.h) via the
 * fallback below. NOTE: this fallback only reaches translation units that
 * include this header; a suite with separate TUs (e.g. a standalone
 * tests/test_helpers.o) must still define SUITE_*_MODE in its Makefile so
 * it is emitted as a global -D visible in every TU.
 * =================================================================== */
#ifndef SUITE_HGATP_MODE
#define SUITE_HGATP_MODE   PLATFORM_HGATP_MODE
#endif

#ifndef SUITE_VSATP_MODE
#define SUITE_VSATP_MODE   PLATFORM_SATP_MODE
#endif

#endif /* TWO_STAGE_HELPERS_H */
