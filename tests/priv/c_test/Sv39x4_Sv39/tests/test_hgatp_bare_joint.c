/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 25: hgatp=Bare joint behavior (TS-BARE-01..06)
 *
 * G-stage trivial translation intersected with an active VS-stage or
 * joint mechanisms (HLV/HSV, MPRV+MPV, HFENCE.GVMA).
 *
 * Spec anchors:
 *   norm:hgatp_mode_bare_trans - hgatp.MODE=Bare: GPA == SPA without
 *       modification; no memory protection in the trivial translation
 *       (a guest-page-fault can never occur).
 *   norm:H_vm_gpatrans         - guest-page-faults only arise from
 *       G-stage translation failures (unreachable when G=Bare).
 *   norm:hlsv_op               - HLV/HSV act as V=1 with nominal
 *       privilege hstatus.SPVP.
 *   norm:mstatus_mprv_hypervisor - MPRV=1 translates per MPV/MPP.
 *   norm:hfence-gvma_mode      - an hgatp.MODE change must be ordered
 *       by HFENCE.GVMA (rs1=x0), even when either MODE is Bare.
 *   norm:sstatus_sum / norm:sstatus_mxr - SUM/MXR only apply when
 *       page-based virtual memory is in effect.
 * =================================================================== */

#ifndef SUITE_HGATP_MODE
#error "SUITE_HGATP_MODE must be defined before including this file"
#endif
#ifndef SUITE_VSATP_MODE
#error "SUITE_VSATP_MODE must be defined before including this file"
#endif


/* norm:hgatp_mode_bare_trans: guest-page-fault (20/21/23) can never
 * be raised while hgatp.MODE=Bare.
 * cause_is_guest_page_fault() from common/cause_defs.h. */
#define g25_cause_not_guest_fault(c)  (!cause_is_guest_page_fault(c))

/* ===================================================================
 * TS-BARE-01: VS-stage fault codes under a Bare G-stage.
 * With an active VS-stage and hgatp=Bare, a VS-stage translation
 * failure must be reported as a regular page fault (cause=13 here),
 * never as a guest-page-fault.
 * =================================================================== */
TEST_REGISTER(test_ts_bare_01_vs_fault_code);
bool test_ts_bare_01_vs_fault_code(void) {
    TEST_BEGIN("TS-BARE-01: VS-stage fault stays page-fault under G=Bare");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_fault_page;
    /* VS-stage victim PTE V=0; G-stage Bare (no tables at all). */
    ts2_setup_with_vs_victim(&ctx, SUITE_VSATP_MODE, HGATP_MODE_BARE, va, 0);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_load_expect_fault, va);
    TEST_ASSERT("trap triggered", trap_was_triggered());
    uintptr_t cause = trap_get_cause();
    TEST_ASSERT_EQ("cause = load page fault (13), VS-stage origin",
                   cause, (uintptr_t)CAUSE_LOAD_PAGE_FAULT);
    TEST_ASSERT("cause is NOT a guest-page-fault (G-stage Bare)",
                g25_cause_not_guest_fault(cause));
    trap_expect_end();

    ts2_finish(&ctx);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-BARE-02: HLV/HSV pass-through under dual Bare.
 * HLV/HSV always act as V=1 with nominal privilege SPVP; with both
 * stages Bare the access must pass through with GPA == SPA.
 * =================================================================== */
TEST_REGISTER(test_ts_bare_02_hlv_hsv);
bool test_ts_bare_02_hlv_hsv(void) {
    TEST_BEGIN("TS-BARE-02: HLV/HSV pass-through (dual Bare)");

    two_stage_ctx_t ctx;
    ts2_setup_full(&ctx, SATP_MODE_BARE, HGATP_MODE_BARE);
    two_stage_enable(&ctx, /*vmid*/0);

    uintptr_t gpa = (uintptr_t)test_data_area;
    hstatus_set_spvp(PRIV_S);

    trap_expect_begin();
    hsv_d(gpa, 0xCAFEBABE0BADF00DULL);
    uint64_t v = hlv_d(gpa);
    bool fired = trap_was_triggered();
    trap_expect_end();

    ts2_finish(&ctx);
    TEST_ASSERT("no trap on HSV.D/HLV.D under dual Bare", !fired);
    TEST_ASSERT_EQ("HLV.D reads the HSV.D-written value (GPA==SPA)",
                   v, 0xCAFEBABE0BADF00DULL);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-BARE-03: MPRV+MPV pass-through under dual Bare.
 * M-mode accesses with MPRV=1, MPV=1, MPP=VS translate as a V=1
 * VS-level access; with both stages Bare this is trivial.
 * =================================================================== */

/* Single-instruction ld/sd inside an MPRV=1 window (no stack access
 * inside the window; mirrors the Group 14 MPRV pattern). */
static inline uint64_t g25_mprv_ld_d(uintptr_t addr)
{
    uint64_t v;
    asm volatile (
        "csrs mstatus, %1\n\t"
        "ld   %0, 0(%2)\n\t"
        "csrc mstatus, %1\n\t"
        : "=&r"(v)
        : "r"((uintptr_t)MSTATUS_MPRV_BIT), "r"(addr)
        : "memory");
    return v;
}

static inline void g25_mprv_sd_d(uintptr_t addr, uint64_t val)
{
    asm volatile (
        "csrs mstatus, %0\n\t"
        "sd   %1, 0(%2)\n\t"
        "csrc mstatus, %0\n\t"
        :
        : "r"((uintptr_t)MSTATUS_MPRV_BIT), "r"(val), "r"(addr)
        : "memory");
}

/* Pre-program mstatus.MPV / MPP outside the MPRV window. M-mode
 * only: MPV/MPP are xret return-path bits, unreachable from below M
 * and refused by the tsbi_csr_* proxy guard. */
static inline void g25_set_mpv_mpp(int mpv, unsigned mpp)
{
    CSRC(CSR_MSTATUS, (uintptr_t)MSTATUS_MPP_MASK);
    if (mpv) {
        CSRS(CSR_MSTATUS, (uintptr_t)MSTATUS_MPV);
    } else {
        CSRC(CSR_MSTATUS, (uintptr_t)MSTATUS_MPV);
    }
    CSRS(CSR_MSTATUS, ((uintptr_t)mpp) << MSTATUS_MPP_OFF);
}

static inline void g25_clear_mpv_mpp(void)
{
    CSRC(CSR_MSTATUS, (uintptr_t)(MSTATUS_MPV | MSTATUS_MPP_MASK));
}

/* The suite now runs in HS-mode, but MPRV only redirects M-mode
 * accesses and MPRV/MPV/MPP are mstatus return-path bits (not
 * proxyable from below M). The ld/sd-inside-MPRV-window sequences
 * therefore run as M-mode excursions via run_in_priv(PRIV_M). The
 * target address is handed over through g25_mprv_addr; the store
 * value rides on the callback argument. Each callback restores
 * MPV=0/MPP=0 before returning so the excursion return path sees a
 * clean mstatus. */
static volatile uintptr_t g25_mprv_addr;

static uintptr_t g25_m_mprv_ld(uintptr_t arg)
{
    (void)arg;
    g25_set_mpv_mpp(/*mpv*/1, /*mpp*/PRIV_S);
    uint64_t v = g25_mprv_ld_d(g25_mprv_addr);
    g25_clear_mpv_mpp();
    return (uintptr_t)v;
}

static uintptr_t g25_m_mprv_sd(uintptr_t arg)
{
    g25_set_mpv_mpp(/*mpv*/1, /*mpp*/PRIV_S);
    g25_mprv_sd_d(g25_mprv_addr, (uint64_t)arg);
    g25_clear_mpv_mpp();
    return 0;
}

TEST_REGISTER(test_ts_bare_03_mprv_mpv);
bool test_ts_bare_03_mprv_mpv(void) {
    TEST_BEGIN("TS-BARE-03: MPRV+MPV pass-through (dual Bare)");

    two_stage_ctx_t ctx;
    ts2_setup_full(&ctx, SATP_MODE_BARE, HGATP_MODE_BARE);
    two_stage_enable(&ctx, /*vmid*/0);

    uintptr_t addr = (uintptr_t)test_data_area;
    *(volatile uint64_t *)addr = 0xA5A5A5A5A5A5A5A5ULL;

    /* MPV=1 + MPP=VS, then load inside an MPRV=1 window: the access
     * is translated as V=1 VS-level -> trivial under dual Bare. The
     * mstatus programming and the windowed ld/sd run in M-mode
     * (MPRV semantics only exist there); see the excursion helpers. */
    g25_mprv_addr = addr;
    uint64_t v = (uint64_t)run_in_priv(PRIV_M, g25_m_mprv_ld, 0);
    TEST_ASSERT_EQ("MPRV load passes through (GPA==SPA)",
                   v, 0xA5A5A5A5A5A5A5A5ULL);

    /* Store inside an MPRV=1 window, verify afterwards from HS-mode. */
    (void)run_in_priv(PRIV_M, g25_m_mprv_sd,
                      (uintptr_t)0x5A5A5A5A5A5A5A5AULL);

    ts2_finish(&ctx);
    TEST_ASSERT_EQ("MPRV store passes through (GPA==SPA)",
                   *(volatile uint64_t *)addr, 0x5A5A5A5A5A5A5A5AULL);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-BARE-04: Bare -> Sv*x4 mode switch.
 * hgatp.MODE changes from Bare to SUITE_HGATP_MODE; per
 * norm:hfence-gvma_mode an HFENCE.GVMA (rs1=x0) must order subsequent
 * guest translations with the change. After the fence, accesses must
 * succeed through the newly activated G-stage identity mapping.
 * =================================================================== */
TEST_REGISTER(test_ts_bare_04_bare_to_sv);
bool test_ts_bare_04_bare_to_sv(void) {
    TEST_BEGIN("TS-BARE-04: Bare -> Sv*x4 switch with HFENCE.GVMA");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    gpt_pool_reset();
    two_stage_init(&ctx, SATP_MODE_BARE, SUITE_HGATP_MODE);

    /* Pre-build the identity G-stage mapping while hgatp is Bare. */
    uintptr_t base = PLATFORM_MEM_BASE & ~(PAGE_SIZE_1G - 1);
    int ret = two_stage_setup_identity(&ctx, base, PAGE_SIZE_1G,
                                       G_FLAGS_RWXU_AD, PT_LEVEL_1G);
    TEST_ASSERT("G-stage identity setup", ret == 0);

    uintptr_t target = (uintptr_t)test_data_area;
    *(volatile uint64_t *)target = 0;

    /* two_stage_enable performs the Bare -> Sv*x4 MODE change. */
    two_stage_enable(&ctx, /*vmid*/0);
    /* Order subsequent guest translations with the MODE change. */
    hfence_gvma_all();

    trap_expect_begin();
    uintptr_t r = run_in_vs_mode(test_vs_read_write, target);
    bool fired = trap_was_triggered();
    trap_expect_end();

    two_stage_cleanup(&ctx);
    hyp_reset_state();
    TEST_ASSERT("no trap after Bare -> Sv*x4 switch", !fired);
    TEST_ASSERT_EQ("VS-mode r/w succeeds under new G-stage mode", r, 0UL);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-BARE-05: Sv*x4 -> Bare mode switch.
 * After a successful access under SUITE_HGATP_MODE, switch hgatp back
 * to Bare with an ordering HFENCE.GVMA; the same GPA must then pass
 * through trivially with no residual G-stage translation.
 * =================================================================== */
TEST_REGISTER(test_ts_bare_05_sv_to_bare);
bool test_ts_bare_05_sv_to_bare(void) {
    TEST_BEGIN("TS-BARE-05: Sv*x4 -> Bare switch with HFENCE.GVMA");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    gpt_pool_reset();
    two_stage_init(&ctx, SATP_MODE_BARE, SUITE_HGATP_MODE);

    uintptr_t base = PLATFORM_MEM_BASE & ~(PAGE_SIZE_1G - 1);
    int ret = two_stage_setup_identity(&ctx, base, PAGE_SIZE_1G,
                                       G_FLAGS_RWXU_AD, PT_LEVEL_1G);
    TEST_ASSERT("G-stage identity setup", ret == 0);

    uintptr_t target = (uintptr_t)test_data_area;
    *(volatile uint64_t *)target = 0;

    /* Phase 1: access succeeds under Sv*x4. */
    uintptr_t r = two_stage_run_in_vs(&ctx, test_vs_read_write, target);
    TEST_ASSERT_EQ("r/w succeeds under Sv*x4", r, 0UL);

    /* Phase 2: switch back to Bare + ordering HFENCE.GVMA. */
    hgatp_set_bare();
    hfence_gvma_all();

    trap_expect_begin();
    r = run_in_vs_mode(test_vs_read_write, target);
    bool fired = trap_was_triggered();
    trap_expect_end();

    two_stage_cleanup(&ctx);
    hyp_reset_state();
    TEST_ASSERT("no trap after Sv*x4 -> Bare switch", !fired);
    TEST_ASSERT_EQ("pass-through succeeds, no residual translation",
                   r, 0UL);
    HYP_TEST_END();
}

/* ===================================================================
 * TS-BARE-06: SUM/MXR have no effect under dual Bare.
 * With no page-based translation active at either stage, setting
 * vsstatus.SUM and vsstatus.MXR must not change access behavior.
 * =================================================================== */
TEST_REGISTER(test_ts_bare_06_sum_mxr_noop);
bool test_ts_bare_06_sum_mxr_noop(void) {
    TEST_BEGIN("TS-BARE-06: SUM/MXR ineffective under dual Bare");

    two_stage_ctx_t ctx;
    ts2_setup_full(&ctx, SATP_MODE_BARE, HGATP_MODE_BARE);

    /* vsstatus.SUM=1 + vsstatus.MXR=1 (CSR 0x200). */
    uintptr_t bits = MSTATUS_SUM_BIT | MSTATUS_MXR_BIT;
    CSRS(CSR_VSSTATUS, bits);

    uintptr_t target = (uintptr_t)test_data_area;
    trap_expect_begin();
    uintptr_t r = two_stage_run_in_vs(&ctx, test_vs_read_write, target);
    bool fired = trap_was_triggered();
    trap_expect_end();

    CSRC(CSR_VSSTATUS, bits);
    ts2_finish(&ctx);
    TEST_ASSERT("no trap with SUM/MXR set under dual Bare", !fired);
    TEST_ASSERT_EQ("access behaves identically to SUM/MXR=0", r, 0UL);
    HYP_TEST_END();
}
