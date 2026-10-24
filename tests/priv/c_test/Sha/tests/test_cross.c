/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 5: Cross-extension interaction tests
 *
 * Spec anchors:
 *   norm:shvstvala_vstval_written    — vstval written on page fault
 *   norm:shtvala_htval_faulting_gpa   — htval = GPA >> 2 on GPF
 *   norm:shvsatpa_satp_vsatp_modes   — satp modes in vsatp
 *   norm:shgatpa_satp_hgatp_mode_support — SvNN -> SvNNx4
 *
 * 5 tests: SHA-CROSS-01 ~ SHA-CROSS-05
 * =================================================================== */

/* ---- VS trap handler (defined in sha_strap.S) ---- */
extern void sha_vs_trap_entry(void);
extern char sha_vs_trap_scratch[];
extern volatile uintptr_t g_sha_vs_cause;
extern volatile uintptr_t g_sha_vs_tval;

/* Unmapped VA for VS-stage page-fault tests (within Sv39 range,
 * but NOT mapped in VS-stage page tables). */
#define SHA_UNMAPPED_VA     0x40000000UL

/* VS-mode payload: set up vstvec + vsscratch, then load from addr.
 * If a delegated page-fault occurs, the VS handler records cause/tval
 * and advances sepc past the faulting instruction. */
static uintptr_t _vs_load_with_trap(uintptr_t addr)
{
    /* Install VS trap handler */
    asm volatile ("csrw stvec, %0" :: "r"((uintptr_t)sha_vs_trap_entry));
    asm volatile ("csrw sscratch, %0" :: "r"((uintptr_t)sha_vs_trap_scratch));

    /* Clear trap globals */
    g_sha_vs_cause = 0;
    g_sha_vs_tval  = 0;

    /* Trigger the load — may fault */
    volatile uintptr_t *ptr = (volatile uintptr_t *)addr;
    (void)*ptr;
    return 0;
}

/* Simple VS-mode load (no VS trap handler setup — trap goes to M-mode) */
static uintptr_t _vs_do_load(uintptr_t addr) {
    uintptr_t val;
    asm volatile ("ld %0, 0(%1)" : "=r"(val) : "r"(addr));
    return val;
}

/* ---- SHA-CROSS-01: Shvstvala existence (vstval written on VS fault) ---- */

TEST_REGISTER(test_sha_cross_shvstvala_vstval);
bool test_sha_cross_shvstvala_vstval(void) {
    TEST_BEGIN("SHA-CROSS-01: Shvstvala — VS page fault writes vstval");
    REQUIRE_HGATP_MODE(HGATP_MODE_SV39X4);
    REQUIRE_SATP_MODE(SATP_MODE_SV39);

    /* Strategy: Set up two-stage with VS=Sv39 + G=Sv39x4.
     * Identity-map kernel region in both stages, but leave
     * SHA_UNMAPPED_VA (0x40000000) unmapped in VS-stage.
     * Delegate load page-fault (cause=13) to VS-mode.
     * VS handler records vscause and vstval. */

    /* Delegate load page-fault to VS-mode */
    hyp_delegate_to_vs((1UL << 13), 0);

    /* Set up two-stage: VS=Sv39, G=Sv39x4 */
    two_stage_ctx_t ctx;
    gpt_pool_reset();
    two_stage_init(&ctx, SATP_MODE_SV39, HGATP_MODE_SV39X4);

    /* VS-stage: identity-map kernel at 2MB */
    uintptr_t lo_base = PLATFORM_MEM_BASE & ~(PAGE_SIZE_2M - 1);
    uintptr_t vs_flags = PTE_V | PTE_R | PTE_W | PTE_X | PTE_A | PTE_D;
    two_stage_vs_identity(&ctx, lo_base, PLATFORM_MEM_SIZE,
                          vs_flags, PT_LEVEL_2M);

    /* G-stage: full identity map */
    two_stage_setup_identity(&ctx, lo_base, PLATFORM_MEM_SIZE,
                             G_FLAGS_RWXU_AD, PT_LEVEL_2M);

    /* Run in VS-mode: load from unmapped VA -> VS page fault */
    two_stage_run_in_vs(&ctx, _vs_load_with_trap, SHA_UNMAPPED_VA);

    /* Verify VS handler recorded the fault */
    TEST_ASSERT_EQ("vscause == load page-fault (13)",
                   g_sha_vs_cause, (uintptr_t)13);
    TEST_ASSERT("vstval != 0 (Shvstvala: vstval written)",
                g_sha_vs_tval != 0);
    TEST_ASSERT_EQ("vstval == faulting VA",
                   g_sha_vs_tval, SHA_UNMAPPED_VA);

    two_stage_cleanup(&ctx);
    hyp_undelegate();
    HYP_TEST_END();
}

/* ---- SHA-CROSS-02: Shtvala existence (htval written on G-stage fault) ---- */

TEST_REGISTER(test_sha_cross_shtvala_htval);
bool test_sha_cross_shtvala_htval(void) {
    TEST_BEGIN("SHA-CROSS-02: Shtvala — G-stage fault writes htval");
    REQUIRE_HGATP_MODE(HGATP_MODE_SV39X4);

    /* Set up G-stage with a known unmapped GPA. Access from VS-mode
     * triggers guest page fault -> htval = GPA >> 2. */

    /* Use a GPA that's definitely unmapped: 0x50000000 region */
    uintptr_t target_gpa = 0x50000000UL;

    gpt_pool_reset();
    gpt_context_t gctx;
    gpt_init(&gctx, HGATP_MODE_SV39X4);

    /* Identity-map kernel/UART region for VS-mode to execute */
    uintptr_t base = PLATFORM_MEM_BASE & ~(PAGE_SIZE_2M - 1);
    gpt_setup_identity_mapping(&gctx, base, PLATFORM_MEM_SIZE,
                               G_FLAGS_RWXU_AD, PT_LEVEL_2M);
    /* Do NOT map target_gpa */

    gpt_enable(&gctx, 0);

    /* Set vsatp=Bare (no VS-stage translation) */
    vsatp_write(0);

    /* Disable M-mode timer interrupt to protect armed flag. mie is M-level and
     * the suite body runs in S(HS)-mode under the T-SBI S-mode-normal boot, so
     * go through the T-SBI CSR proxy instead of a direct access. */
    uintptr_t saved_mie = tsbi_csr_read(CSR_MIE);
    tsbi_csr_clear(CSR_MIE, 1UL << 7);  /* clear MTIE */

    trap_expect_begin();
    run_in_vs_mode(_vs_do_load, target_gpa);
    bool fired = trap_was_triggered();
    uintptr_t cause = fired ? trap_get_cause() : 0;
    uintptr_t htval = fired ? trap_get_htval() : 0;
    trap_expect_end();

    tsbi_csr_write(CSR_MIE, saved_mie);

    gpt_disable();
    hyp_reset_state();

    TEST_ASSERT("G-stage fault triggered", fired);
    if (fired) {
        TEST_ASSERT_EQ("cause == load guest-page-fault (21)",
                       cause, (uintptr_t)CAUSE_LOAD_GUEST_PAGE_FAULT);
        TEST_ASSERT("htval != 0 (Shtvala: htval written)", htval != 0);
        TEST_ASSERT_EQ("htval == GPA >> 2", htval, target_gpa >> 2);
    }

    HYP_TEST_END();
}

/* ---- SHA-CROSS-03: Shvsatpa + Shgatpa mode coherence ---- */

TEST_REGISTER(test_sha_cross_vsatp_hgatp_coherent);
bool test_sha_cross_vsatp_hgatp_coherent(void) {
    TEST_BEGIN("SHA-CROSS-03: vsatp and hgatp both support modes per satp");

    /* Check all three modes: Sv39, Sv48, Sv57 */
    struct {
        int satp_mode;
        int hgatp_mode;
        const char *name;
    } modes[] = {
        { SATP_MODE_SV39, HGATP_MODE_SV39X4, "Sv39/Sv39x4" },
        { SATP_MODE_SV48, HGATP_MODE_SV48X4, "Sv48/Sv48x4" },
        { SATP_MODE_SV57, HGATP_MODE_SV57X4, "Sv57/Sv57x4" },
    };

    bool found_any = false;
    bool all_ok = true;

    for (int i = 0; i < 3; i++) {
        bool satp_ok = satp_supports_mode(modes[i].satp_mode);
        if (!satp_ok) continue;

        found_any = true;

        bool vsatp_ok = vsatp_supports_mode(modes[i].satp_mode);
        bool hgatp_ok = hgatp_supports_mode(modes[i].hgatp_mode);

        if (!vsatp_ok) {
            LOG_E("satp supports %s but vsatp does not\n",
                  modes[i].name);
            all_ok = false;
        }
        if (!hgatp_ok) {
            LOG_E("satp supports %s but hgatp does not\n",
                  modes[i].name);
            all_ok = false;
        }
    }

    if (!found_any) {
        TEST_SKIP("satp supports no SvNN modes");
    }

    TEST_ASSERT("vsatp + hgatp both support all satp modes", all_ok);
    HYP_TEST_END();
}

/* ---- SHA-CROSS-04: Shvstvecd + Shvstvala Direct trap + vstval ---- */

TEST_REGISTER(test_sha_cross_vstvec_direct_vstval);
bool test_sha_cross_vstvec_direct_vstval(void) {
    TEST_BEGIN("SHA-CROSS-04: Shvstvecd Direct + Shvstvala vstval coherence");
    REQUIRE_HGATP_MODE(HGATP_MODE_SV39X4);
    REQUIRE_SATP_MODE(SATP_MODE_SV39);

    /* Verify end-to-end: vstvec Direct mode is used for trap entry,
     * and vstval is written with the faulting address.
     *
     * Set up VS=Sv39 + G=Sv39x4 with identity mapping.
     * Configure vstvec to Direct mode with sha_vs_trap_entry as BASE.
     * Delegate load page-fault to VS-mode.
     * Trigger a load from an unmapped VA in VS-mode.
     * Verify the VS handler was entered via Direct mode and vstval
     * contains the faulting VA. */

    uintptr_t handler_addr = (uintptr_t)sha_vs_trap_entry;

    /* Verify vstvec can hold Direct mode with our handler address */
    uintptr_t saved_vstvec = vstvec_read();
    vstvec_write(handler_addr & ~0x3UL);  /* MODE=Direct */
    uintptr_t vstvec_rb = vstvec_read();
    TEST_ASSERT("vstvec MODE == 0 (Direct)",
                (vstvec_rb & 0x3UL) == 0);
    TEST_ASSERT("vstvec BASE holds handler address",
                (vstvec_rb & ~0x3UL) == (handler_addr & ~0x3UL));

    /* Delegate load page-fault to VS-mode */
    hyp_delegate_to_vs((1UL << 13), 0);

    /* Set up two-stage */
    two_stage_ctx_t ctx;
    gpt_pool_reset();
    two_stage_init(&ctx, SATP_MODE_SV39, HGATP_MODE_SV39X4);

    uintptr_t lo_base = PLATFORM_MEM_BASE & ~(PAGE_SIZE_2M - 1);
    uintptr_t vs_flags = PTE_V | PTE_R | PTE_W | PTE_X | PTE_A | PTE_D;
    two_stage_vs_identity(&ctx, lo_base, PLATFORM_MEM_SIZE,
                          vs_flags, PT_LEVEL_2M);
    two_stage_setup_identity(&ctx, lo_base, PLATFORM_MEM_SIZE,
                             G_FLAGS_RWXU_AD, PT_LEVEL_2M);

    /* Run in VS-mode: load from unmapped VA */
    two_stage_run_in_vs(&ctx, _vs_load_with_trap, SHA_UNMAPPED_VA);

    /* Verify VS handler captured the fault */
    TEST_ASSERT_EQ("vscause == load page-fault (13)",
                   g_sha_vs_cause, (uintptr_t)13);
    TEST_ASSERT_EQ("vstval == faulting VA (Shvstvala)",
                   g_sha_vs_tval, SHA_UNMAPPED_VA);

    two_stage_cleanup(&ctx);
    vstvec_write(saved_vstvec);
    hyp_undelegate();
    HYP_TEST_END();
}

/* ---- SHA-CROSS-05: Shtvala + Shvstvala non-interference ---- */

TEST_REGISTER(test_sha_cross_htval_vstval_independent);
bool test_sha_cross_htval_vstval_independent(void) {
    TEST_BEGIN("SHA-CROSS-05: htval and vstval independent under real traps");
    REQUIRE_HGATP_MODE(HGATP_MODE_SV39X4);
    REQUIRE_SATP_MODE(SATP_MODE_SV39);

    /* Phase 1: Trigger G-stage fault -> htval written, vstval untouched.
     * vsatp=Bare, G-stage with unmapped GPA. */
    uintptr_t gpf_gpa = 0x50000000UL;

    gpt_pool_reset();
    gpt_context_t gctx;
    gpt_init(&gctx, HGATP_MODE_SV39X4);

    uintptr_t base = PLATFORM_MEM_BASE & ~(PAGE_SIZE_2M - 1);
    gpt_setup_identity_mapping(&gctx, base, PLATFORM_MEM_SIZE,
                               G_FLAGS_RWXU_AD, PT_LEVEL_2M);

    gpt_enable(&gctx, 0);
    vsatp_write(0);

    /* Clear vstval before G-stage fault */
    vstval_write(0);

    /* Disable M-mode timer interrupt to protect armed flag. mie is M-level and
     * the suite body runs in S(HS)-mode under the T-SBI S-mode-normal boot, so
     * go through the T-SBI CSR proxy instead of a direct access. */
    uintptr_t saved_mie = tsbi_csr_read(CSR_MIE);
    tsbi_csr_clear(CSR_MIE, 1UL << 7);  /* clear MTIE */

    trap_expect_begin();
    run_in_vs_mode(_vs_do_load, gpf_gpa);
    bool gpf_fired = trap_was_triggered();
    uintptr_t gpf_cause = gpf_fired ? trap_get_cause() : 0;
    uintptr_t gpf_htval = gpf_fired ? trap_get_htval() : 0;
    uintptr_t vstval_after_gpf = vstval_read();
    trap_expect_end();

    tsbi_csr_write(CSR_MIE, saved_mie);

    gpt_disable();
    hyp_reset_state();

    TEST_ASSERT("Phase 1: G-stage fault triggered", gpf_fired);
    if (gpf_fired) {
        TEST_ASSERT_EQ("Phase 1: cause == load guest-page-fault (21)",
                       gpf_cause, (uintptr_t)CAUSE_LOAD_GUEST_PAGE_FAULT);
        TEST_ASSERT("Phase 1: htval != 0 (Shtvala)", gpf_htval != 0);
        TEST_ASSERT_EQ("Phase 1: htval == GPA >> 2",
                       gpf_htval, gpf_gpa >> 2);
        TEST_ASSERT_EQ("Phase 1: vstval not modified by G-stage fault",
                       vstval_after_gpf, (uintptr_t)0);
    }

    /* Phase 2: Trigger VS-stage fault -> vstval written independently.
     * htval from Phase 1 is retained (not cleared), but the key
     * assertion is that vstval is independently written by hardware. */
    hyp_delegate_to_vs((1UL << 13), 0);

    two_stage_ctx_t ctx;
    gpt_pool_reset();
    two_stage_init(&ctx, SATP_MODE_SV39, HGATP_MODE_SV39X4);

    uintptr_t vs_flags = PTE_V | PTE_R | PTE_W | PTE_X | PTE_A | PTE_D;
    two_stage_vs_identity(&ctx, base, PLATFORM_MEM_SIZE,
                          vs_flags, PT_LEVEL_2M);
    two_stage_setup_identity(&ctx, base, PLATFORM_MEM_SIZE,
                             G_FLAGS_RWXU_AD, PT_LEVEL_2M);

    two_stage_run_in_vs(&ctx, _vs_load_with_trap, SHA_UNMAPPED_VA);

    TEST_ASSERT_EQ("Phase 2: vscause == load page-fault (13)",
                   g_sha_vs_cause, (uintptr_t)13);
    TEST_ASSERT("Phase 2: vstval != 0 (Shvstvala)", g_sha_vs_tval != 0);
    TEST_ASSERT_EQ("Phase 2: vstval == faulting VA",
                   g_sha_vs_tval, SHA_UNMAPPED_VA);

    two_stage_cleanup(&ctx);
    hyp_undelegate();
    HYP_TEST_END();
}
