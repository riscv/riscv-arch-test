/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 4: V=1 transparent semantics (satp access operates vsatp)
 *
 * Spec anchors:
 *   norm:vsatp_sz_acc_op (hypervisor.adoc:1384-1392):
 *     "When V=1, vsatp substitutes for the usual satp, so
 *      instructions that normally read or modify satp actually
 *      access vsatp instead."
 *
 * Test list (matches DOCS/testplan/shvsatpa_test_plan.md VSATP-TRANS):
 *   VSATP-TRANS-01  VS writes satp -> M reads vsatp
 *   VSATP-TRANS-02  M writes vsatp -> VS reads satp
 *   VSATP-TRANS-03  VS writes satp does NOT affect HS-mode satp
 *
 * IMPLEMENTATION NOTE:
 *   Writing non-Bare MODE to vsatp/satp in VS-mode immediately enables
 *   VS-stage address translation on QEMU. To avoid instruction page
 *   faults, all three tests use two_stage_run_in_vs which provides
 *   identity-mapped VS-stage + G-stage page tables. The VS-mode helper
 *   only writes satp=Bare (safe direction: SvNN -> identity).
 * =================================================================== */

extern volatile bool g_satp_supports_sv39;

/* Volatile for VS<->M data passing */
static volatile uintptr_t g_trans_vs_read;

/* VS-mode helper: write satp = Bare (safe direction) */
static uintptr_t vsmode_trans_write_bare(uintptr_t arg) {
    (void)arg;
    asm volatile ("csrw satp, zero" ::: "memory");
    return 0;
}

/* VS-mode helper: read satp and store in global */
static uintptr_t vsmode_trans_read(uintptr_t arg) {
    (void)arg;
    uintptr_t val;
    asm volatile ("csrr %0, satp" : "=r"(val));
    g_trans_vs_read = val;
    return 0;
}

/* VS-mode helper: read satp, then write Bare, read again */
static uintptr_t vsmode_trans_read_write_bare(uintptr_t arg) {
    (void)arg;
    uintptr_t val;
    asm volatile ("csrr %0, satp" : "=r"(val));
    g_trans_vs_read = val;
    /* Write Bare (safe direction) */
    asm volatile ("csrw satp, zero" ::: "memory");
    return 0;
}

/* Common helper: set up two-stage context and run a VS helper.
 * Returns the two_stage_ctx_t for further inspection / cleanup. */
static bool _trans_setup_two_stage(two_stage_ctx_t *ctx, int vs_mode, int g_mode) {
    gpt_pool_reset();
    two_stage_init(ctx, vs_mode, g_mode);

    uintptr_t base  = PLATFORM_MEM_BASE & ~(PAGE_SIZE_2M - 1);
    uintptr_t size  = PLATFORM_MEM_SIZE;
    uintptr_t vs_fl = PTE_V | PTE_R | PTE_W | PTE_X | PTE_A | PTE_D;
    uintptr_t g_fl  = G_FLAGS_RWXU_AD;

    two_stage_vs_identity(ctx, base, size, vs_fl, PT_LEVEL_2M);
    two_stage_setup_identity(ctx, base, size, g_fl, PT_LEVEL_2M);
    return true;
}

/* ---- VSATP-TRANS-01 ---- */
TEST_REGISTER(test_shvsatpa_trans_vs_write_m_read);
bool test_shvsatpa_trans_vs_write_m_read(void) {
    TEST_BEGIN("VSATP-TRANS-01: VS writes satp, M reads vsatp");

    if (!g_satp_supports_sv39) {
        TEST_SKIP("satp does not support Sv39 (needed for non-trivial transparency test)");
    }
    REQUIRE_HGATP_MODE(HGATP_MODE_SV39X4);

    two_stage_ctx_t ctx;
    _trans_setup_two_stage(&ctx, SATP_MODE_SV39, HGATP_MODE_SV39X4);

    /* two_stage_enable (called inside two_stage_run_in_vs) will set
     * vsatp = Sv39 + root PPN.  VS-mode writes satp = Bare. */
    two_stage_run_in_vs(&ctx, vsmode_trans_write_bare, 0);

    /* M reads vsatp: should now be Bare (VS wrote it via satp) */
    uintptr_t m_vsatp_mode = SATP_GET_MODE(vsatp_read());
    TEST_ASSERT_EQ("M reads vsatp.MODE == Bare (VS wrote satp=Bare)",
                   m_vsatp_mode, (uintptr_t)SATP_MODE_BARE);

    two_stage_cleanup(&ctx);
    HYP_TEST_END();
}

/* ---- VSATP-TRANS-02 ---- */
TEST_REGISTER(test_shvsatpa_trans_m_write_vs_read);
bool test_shvsatpa_trans_m_write_vs_read(void) {
    TEST_BEGIN("VSATP-TRANS-02: M writes vsatp, VS reads satp");

    if (!g_satp_supports_sv39) {
        TEST_SKIP("satp does not support Sv39 (needed for non-trivial transparency test)");
    }
    REQUIRE_HGATP_MODE(HGATP_MODE_SV39X4);

    two_stage_ctx_t ctx;
    _trans_setup_two_stage(&ctx, SATP_MODE_SV39, HGATP_MODE_SV39X4);

    g_trans_vs_read = 0;

    /* two_stage_run_in_vs sets vsatp = Sv39 + root PPN.
     * VS-mode reads satp (actually vsatp) — should see that value. */
    two_stage_run_in_vs(&ctx, vsmode_trans_read, 0);

    /* The value VS read should have MODE=Sv39 */
    uintptr_t vs_mode = SATP_GET_MODE(g_trans_vs_read);
    TEST_ASSERT_EQ("VS reads satp.MODE == Sv39 (M set vsatp)",
                   vs_mode, (uintptr_t)SATP_MODE_SV39);

    /* Cross-check: M reads vsatp, should match what VS read (same mode) */
    uintptr_t m_mode = SATP_GET_MODE(vsatp_read());
    TEST_ASSERT_EQ("M reads vsatp.MODE == Sv39 (consistent)",
                   m_mode, (uintptr_t)SATP_MODE_SV39);

    two_stage_cleanup(&ctx);
    HYP_TEST_END();
}

/* ---- VSATP-TRANS-03 ---- */
TEST_REGISTER(test_shvsatpa_trans_vs_no_affect_hs_satp);
bool test_shvsatpa_trans_vs_no_affect_hs_satp(void) {
    TEST_BEGIN("VSATP-TRANS-03: VS writes satp does NOT affect HS satp");

    if (!g_satp_supports_sv39) {
        TEST_SKIP("satp does not support Sv39 (needed for non-trivial isolation test)");
    }
    REQUIRE_HGATP_MODE(HGATP_MODE_SV39X4);

    /* Save and set HS satp to known Bare value */
    uintptr_t saved_hs_satp = satp_read();
    satp_write(MAKE_SATP(SATP_MODE_BARE, 0, 0));
    uintptr_t hs_before = satp_read();

    two_stage_ctx_t ctx;
    _trans_setup_two_stage(&ctx, SATP_MODE_SV39, HGATP_MODE_SV39X4);

    g_trans_vs_read = 0;

    /* VS reads satp (should see Sv39, not HS's Bare),
     * then writes satp = Bare (safe direction). */
    two_stage_run_in_vs(&ctx, vsmode_trans_read_write_bare, 0);

    /* Verify VS saw Sv39 (vsatp), not Bare (HS satp) */
    uintptr_t vs_read_mode = SATP_GET_MODE(g_trans_vs_read);
    TEST_ASSERT_EQ("VS reads satp.MODE == Sv39 (vsatp, not HS satp)",
                   vs_read_mode, (uintptr_t)SATP_MODE_SV39);

    /* HS satp must remain unchanged */
    uintptr_t hs_after = satp_read();
    TEST_ASSERT_EQ("HS satp unchanged after VS writes satp",
                   hs_after, hs_before);

    two_stage_cleanup(&ctx);
    satp_write(saved_hs_satp);
    HYP_TEST_END();
}
