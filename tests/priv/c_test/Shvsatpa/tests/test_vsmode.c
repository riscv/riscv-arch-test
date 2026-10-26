/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 3: VS-mode (V=1) verification via satp instruction
 *
 * Spec anchors:
 *   norm:shvsatpa_satp_vsatp_modes (shvsatpa.adoc:4-6)
 *   norm:vsatp_sz_acc_op           (hypervisor.adoc:1384-1392)
 *   norm:vsatp_mode_unsupported_v1 (hypervisor.adoc:1417-1418)
 *
 * Test list (matches DOCS/testplan/shvsatpa_test_plan.md VSATP-VS):
 *   VSATP-VS-01  VS-mode writes satp MODE=Bare (actually vsatp)
 *   VSATP-VS-02  VS-mode writes satp MODE=Sv39
 *   VSATP-VS-03  VS-mode writes satp MODE=Sv48
 *   VSATP-VS-04  VS-mode writes satp MODE=Sv57
 *
 * In VS-mode (V=1), the `satp` instruction name accesses vsatp.
 * These tests write MODE via that path and cross-verify from M-mode.
 *
 * IMPLEMENTATION NOTE:
 *   Writing a non-Bare MODE to vsatp in VS-mode immediately enables
 *   VS-stage address translation on QEMU (no sfence needed). To avoid
 *   instruction page faults, VSATP-VS-02/03/04 use two_stage_run_in_vs
 *   which sets up identity-mapped VS-stage page tables. The VS-mode
 *   helper reads satp (verifies the pre-set MODE), then writes
 *   satp=Bare (safe: SvNN -> identity) and reads back to confirm.
 * =================================================================== */

extern volatile bool g_satp_supports_sv39;
extern volatile bool g_satp_supports_sv48;
extern volatile bool g_satp_supports_sv57;

/* Volatile for VS->M data passing */
static volatile uintptr_t g_vsmode_read_before;
static volatile uintptr_t g_vsmode_read_after;

/* VS-mode helper for VSATP-VS-01 (Bare): write and read */
static uintptr_t vsmode_write_bare_readback(uintptr_t arg) {
    (void)arg;
    asm volatile ("csrw satp, zero" ::: "memory");
    uintptr_t rb;
    asm volatile ("csrr %0, satp" : "=r"(rb));
    g_vsmode_read_after = rb;
    return 0;
}

/* VS-mode helper for VSATP-VS-02/03/04:
 * Read satp (pre-set MODE), then write Bare, read back again. */
static uintptr_t vsmode_read_write_bare(uintptr_t arg) {
    (void)arg;
    uintptr_t before;
    asm volatile ("csrr %0, satp" : "=r"(before));
    g_vsmode_read_before = before;

    /* Write Bare (safe direction: SvNN -> identity) */
    asm volatile ("csrw satp, zero" ::: "memory");

    uintptr_t after;
    asm volatile ("csrr %0, satp" : "=r"(after));
    g_vsmode_read_after = after;
    return 0;
}

/* ---- VSATP-VS-01 ---- */
TEST_REGISTER(test_shvsatpa_vsmode_bare);
bool test_shvsatpa_vsmode_bare(void) {
    TEST_BEGIN("VSATP-VS-01: VS-mode writes satp MODE=Bare (actually vsatp)");

    uintptr_t saved = vsatp_read();
    vsatp_write(MAKE_SATP(SATP_MODE_BARE, 0, 0));

    g_vsmode_read_after = ~0UL;
    run_in_vs_mode(vsmode_write_bare_readback, 0);

    uintptr_t vs_mode = SATP_GET_MODE(g_vsmode_read_after);
    TEST_ASSERT_EQ("VS-mode readback satp.MODE == Bare",
                   vs_mode, (uintptr_t)SATP_MODE_BARE);

    /* M-mode cross-check */
    uintptr_t m_mode = SATP_GET_MODE(vsatp_read());
    TEST_ASSERT_EQ("M-mode reads vsatp.MODE == Bare (cross-check)",
                   m_mode, (uintptr_t)SATP_MODE_BARE);

    vsatp_write(saved);
    HYP_TEST_END();
}

/* Helper: set up two-stage identity-mapped context and run the VS
 * helper. Verifies that the pre-set MODE reads correctly from VS-mode
 * and that a VS-mode write of Bare is reflected. */
static bool _vsmode_test_mode(int vs_mode, int g_mode,
                              const char *mode_name, uintptr_t expected_mode) {
    REQUIRE_HGATP_MODE(g_mode);

    two_stage_ctx_t ctx;
    gpt_pool_reset();
    two_stage_init(&ctx, vs_mode, g_mode);

    /* Identity-map entire memory at both stages (2MB superpages) */
    uintptr_t base  = PLATFORM_MEM_BASE & ~(PAGE_SIZE_2M - 1);
    uintptr_t size  = PLATFORM_MEM_SIZE;
    uintptr_t vs_fl = PTE_V | PTE_R | PTE_W | PTE_X | PTE_A | PTE_D;
    uintptr_t g_fl  = G_FLAGS_RWXU_AD;

    two_stage_vs_identity(&ctx, base, size, vs_fl, PT_LEVEL_2M);
    two_stage_setup_identity(&ctx, base, size, g_fl, PT_LEVEL_2M);

    g_vsmode_read_before = 0;
    g_vsmode_read_after  = ~0UL;

    two_stage_run_in_vs(&ctx, vsmode_read_write_bare, 0);

    /* VS-mode read of pre-set MODE */
    uintptr_t before_mode = SATP_GET_MODE(g_vsmode_read_before);
    TEST_ASSERT_EQ("VS-mode reads satp.MODE (pre-set)",
                   before_mode, expected_mode);

    /* VS-mode write of Bare */
    uintptr_t after_mode = SATP_GET_MODE(g_vsmode_read_after);
    TEST_ASSERT_EQ("VS-mode readback after writing Bare",
                   after_mode, (uintptr_t)SATP_MODE_BARE);

    /* M-mode cross-check: vsatp should now be Bare */
    uintptr_t m_mode = SATP_GET_MODE(vsatp_read());
    TEST_ASSERT_EQ("M-mode reads vsatp.MODE == Bare (cross-check)",
                   m_mode, (uintptr_t)SATP_MODE_BARE);

    two_stage_cleanup(&ctx);
    return true;  /* assertions handled by macros */
}

/* ---- VSATP-VS-02 ---- */
TEST_REGISTER(test_shvsatpa_vsmode_sv39);
bool test_shvsatpa_vsmode_sv39(void) {
    TEST_BEGIN("VSATP-VS-02: VS-mode reads/writes satp MODE=Sv39 (actually vsatp)");

    if (!g_satp_supports_sv39) {
        TEST_SKIP("satp does not support Sv39");
    }

    _vsmode_test_mode(SATP_MODE_SV39, HGATP_MODE_SV39X4,
                      "Sv39", (uintptr_t)SATP_MODE_SV39);

    HYP_TEST_END();
}

/* ---- VSATP-VS-03 ---- */
TEST_REGISTER(test_shvsatpa_vsmode_sv48);
bool test_shvsatpa_vsmode_sv48(void) {
    TEST_BEGIN("VSATP-VS-03: VS-mode reads/writes satp MODE=Sv48 (actually vsatp)");

    if (!g_satp_supports_sv48) {
        TEST_SKIP("satp does not support Sv48");
    }

    _vsmode_test_mode(SATP_MODE_SV48, HGATP_MODE_SV48X4,
                      "Sv48", (uintptr_t)SATP_MODE_SV48);

    HYP_TEST_END();
}

/* ---- VSATP-VS-04 ---- */
TEST_REGISTER(test_shvsatpa_vsmode_sv57);
bool test_shvsatpa_vsmode_sv57(void) {
    TEST_BEGIN("VSATP-VS-04: VS-mode reads/writes satp MODE=Sv57 (actually vsatp)");

    if (!g_satp_supports_sv57) {
        TEST_SKIP("satp does not support Sv57");
    }

    _vsmode_test_mode(SATP_MODE_SV57, HGATP_MODE_SV57X4,
                      "Sv57", (uintptr_t)SATP_MODE_SV57);

    HYP_TEST_END();
}
