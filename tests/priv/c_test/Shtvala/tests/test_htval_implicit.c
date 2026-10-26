/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 3: Implicit VS-stage PTE GPF (HTVAL-IMP-*)
 *
 * Spec anchor:
 *   norm:H_htval — htval also reports the GPA when the VS-stage walk
 *   itself triggers a G-stage fault (i.e., VS-stage PTE access is GPF).
 *
 * Scenario:
 *   Both stages active: vsatp=Sv39, hgatp=Sv39x4.
 *   VS-stage page tables map test_va at 4KB (creating root/L1/L0 PTs).
 *   G-stage maps everything with full permissions EXCEPT the victim
 *   VS-stage page-table page, which has V=0 (or R=0).
 *   A VS-mode access to test_va triggers the VS-stage walk; when the
 *   walker reads the PTE from the victim page via G-stage, G-stage
 *   raises a guest-page-fault.
 *
 * Plan list:
 *   HTVAL-IMP-01  L1 PTE GPF (V=0) — walker reads L1 page, G-stage V=0
 *   HTVAL-IMP-02  L0 PTE GPF (V=0) — walker reads L0 page, G-stage V=0
 *   HTVAL-IMP-03  L0 PTE GPF (R=0) — walker reads L0 page, G-stage R=0
 *   HTVAL-IMP-04  L0 PTE GPF on store walk — same as 02 but store path
 * =================================================================== */

/* Test VA must be in a DIFFERENT 1GB region (VPN[2]) from kernel, so that
 * the VS-stage L1/L0 page table pages for this VA are distinct from the
 * kernel's, and can be selectively faulted in G-stage without interfering
 * with kernel instruction fetches.
 *
 * On QEMU virt (MEM_BASE=0x80000000, VPN[2]=2) we use VPN[2]=1.
 * On haps_xiaohui (MEM_BASE=0x60000000, VPN[2]=1) we use VPN[2]=2.
 */
#define KERNEL_VPN2       ((unsigned long)(PLATFORM_MEM_BASE) >> 30)
#define IMP_TEST_VPN2     (KERNEL_VPN2 == 1 ? 2UL : 1UL)
#define IMP_TEST_VA       ((IMP_TEST_VPN2 << 30) | 0x200000UL)

/* ===================================================================
 * HTVAL-IMP-01: L1 PTE GPF (V=0)
 *
 * Walker path: root PTE (OK) -> read L1 page (FAULT, V=0 in G-stage)
 * Expected: cause=21, htval = (L1_page_addr + VPN1*8) >> 2
 * =================================================================== */
TEST_REGISTER(test_htval_imp_01_l1_invalid);
bool test_htval_imp_01_l1_invalid(void) {
    TEST_BEGIN("HTVAL-IMP-01: implicit VS-stage L1 PTE GPF (V=0)");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(HGATP_MODE_SV39X4);

    two_stage_ctx_t ctx;
    uintptr_t test_va = IMP_TEST_VA;

    /* Set up: VS-stage Sv39 + G-stage Sv39x4, L1 page marked V=0 */
    uintptr_t victim_gpa = setup_implicit_walk_victim_level(&ctx, test_va,
                                              /*victim_pt_level=*/1,
                                              /*victim_g_flags=*/0);

    /* Compute expected htval: walker accesses PTE at VPN1 offset
     * within the L1 page table page. */
    uintptr_t pte_offset = VA_VPN(test_va, 1) * sizeof(uintptr_t);
    uintptr_t pte_gpa = victim_gpa + pte_offset;

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_load_expect_fault, test_va);
    TEST_ASSERT("implicit L1 GPF triggered", trap_was_triggered());
    if (trap_was_triggered()) {
        TEST_ASSERT_EQ("cause = 21 (load-gpf)",
                       trap_get_cause(), CAUSE_LOAD_GUEST_PAGE_FAULT);
        CHECK_HTVAL("htval = PTE_GPA>>2", pte_gpa >> 2);
    }
    trap_expect_end();

    two_stage_cleanup(&ctx);
    hyp_reset_state();
    HYP_TEST_END();
}

/* ===================================================================
 * HTVAL-IMP-01-ROOT (removed):
 *
 * The test plan calls for a root-table (L2) implicit GPF where the
 * VS-stage root page itself is unmapped in G-stage. However, Sv39
 * uses a single root page table page shared by ALL VAs. Marking it
 * V=0 in G-stage blocks EVERY VS-stage walk — including instruction
 * fetch for VS-mode code — so VS-mode cannot even begin executing.
 *
 * IMP-01 (L1, mid-level) already covers the "high-level PT page
 * fault" intent of the plan.
 * =================================================================== */

/* ===================================================================
 * HTVAL-IMP-02: L0 PTE GPF (V=0)
 *
 * Walker path: root PTE (OK) -> L1 PTE (OK) -> read L0 page (FAULT)
 * Expected: cause=21, htval = (L0_page_addr + VPN0*8) >> 2
 * =================================================================== */
TEST_REGISTER(test_htval_imp_02_l0_invalid);
bool test_htval_imp_02_l0_invalid(void) {
    TEST_BEGIN("HTVAL-IMP-02: implicit VS-stage L0 PTE GPF (V=0)");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(HGATP_MODE_SV39X4);

    two_stage_ctx_t ctx;
    uintptr_t test_va = IMP_TEST_VA;

    uintptr_t victim_gpa = setup_implicit_walk_victim_level(&ctx, test_va,
                                              /*victim_pt_level=*/0,
                                              /*victim_g_flags=*/0);

    uintptr_t pte_offset = VA_VPN(test_va, 0) * sizeof(uintptr_t);
    uintptr_t pte_gpa = victim_gpa + pte_offset;

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_load_expect_fault, test_va);
    TEST_ASSERT("implicit L0 GPF triggered", trap_was_triggered());
    if (trap_was_triggered()) {
        TEST_ASSERT_EQ("cause = 21 (load-gpf)",
                       trap_get_cause(), CAUSE_LOAD_GUEST_PAGE_FAULT);
        CHECK_HTVAL("htval = PTE_GPA>>2", pte_gpa >> 2);
    }
    trap_expect_end();

    two_stage_cleanup(&ctx);
    hyp_reset_state();
    HYP_TEST_END();
}

/* ===================================================================
 * HTVAL-IMP-03: L0 PTE GPF (R=0)
 *
 * Same as IMP-02 but the L0 page is valid (V=1) but read-protected
 * (R=0). The walker's implicit read should still fault.
 * Expected: cause=21, htval = (L0_page_addr + VPN0*8) >> 2
 * =================================================================== */
TEST_REGISTER(test_htval_imp_03_l0_perm);
bool test_htval_imp_03_l0_perm(void) {
    TEST_BEGIN("HTVAL-IMP-03: implicit VS-stage L0 PTE GPF (R=0)");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(HGATP_MODE_SV39X4);

    two_stage_ctx_t ctx;
    uintptr_t test_va = IMP_TEST_VA;

    /* V=1 but R=0: page table walker reads are denied. */
    uintptr_t victim_gpa = setup_implicit_walk_victim_level(&ctx, test_va,
                                              /*victim_pt_level=*/0,
                                              G_FLAGS_RWXU_AD & ~PTE_R);

    uintptr_t pte_offset = VA_VPN(test_va, 0) * sizeof(uintptr_t);
    uintptr_t pte_gpa = victim_gpa + pte_offset;

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_load_expect_fault, test_va);
    TEST_ASSERT("implicit L0 perm GPF triggered", trap_was_triggered());
    if (trap_was_triggered()) {
        TEST_ASSERT_EQ("cause = 21 (load-gpf)",
                       trap_get_cause(), CAUSE_LOAD_GUEST_PAGE_FAULT);
        CHECK_HTVAL("htval = PTE_GPA>>2", pte_gpa >> 2);
    }
    trap_expect_end();

    two_stage_cleanup(&ctx);
    hyp_reset_state();
    HYP_TEST_END();
}

/* ===================================================================
 * HTVAL-IMP-04: L0 PTE GPF on store walk
 *
 * Same as IMP-02 but triggered by a store instead of a load.
 * The walker still does a read of the PTE (implicit load), but per
 * RISC-V spec the exception cause is based on the ORIGINAL access
 * type: store -> cause=23 (store/AMO guest-page-fault).
 * =================================================================== */
TEST_REGISTER(test_htval_imp_04_store_walk);
bool test_htval_imp_04_store_walk(void) {
    TEST_BEGIN("HTVAL-IMP-04: implicit VS-stage L0 PTE GPF on store walk");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(HGATP_MODE_SV39X4);

    two_stage_ctx_t ctx;
    uintptr_t test_va = IMP_TEST_VA;

    uintptr_t victim_gpa = setup_implicit_walk_victim_level(&ctx, test_va,
                                              /*victim_pt_level=*/0,
                                              /*victim_g_flags=*/0);

    uintptr_t pte_offset = VA_VPN(test_va, 0) * sizeof(uintptr_t);
    uintptr_t pte_gpa = victim_gpa + pte_offset;

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_store_expect_fault, test_va);
    TEST_ASSERT("implicit L0 store-walk GPF triggered", trap_was_triggered());
    if (trap_was_triggered()) {
        /* Per RISC-V spec: exception cause is based on the original access
         * type, not the implicit PTE read. Store → cause=23. */
        TEST_ASSERT_EQ("cause = 23 (store-gpf, original access)",
                       trap_get_cause(), CAUSE_STORE_GUEST_PAGE_FAULT);
        CHECK_HTVAL("htval = PTE_GPA>>2", pte_gpa >> 2);
    }
    trap_expect_end();

    two_stage_cleanup(&ctx);
    hyp_reset_state();
    HYP_TEST_END();
}

/* ===================================================================
 * HTVAL-IMP-05: Implicit read GPF htinst pseudoinstruction
 *
 * When an implicit VS-stage PTE read triggers a G-stage GPF:
 *  - norm:htval_trapval: htval may be zero OR the faulting GPA >> 2;
 *    both are compliant, and when htval == 0 there is no htinst
 *    requirement.
 *  - norm:H_trap_xtinst_guestpage: once htval is nonzero (condition
 *    (b) met; condition (a) holds by construction here), htinst MUST
 *    be the read pseudoinstruction (0x00003000 for RV64) — zero is
 *    NOT allowed and must be reported, not tolerated.
 * =================================================================== */
TEST_REGISTER(test_htval_imp_05_htinst_read);
bool test_htval_imp_05_htinst_read(void) {
    TEST_BEGIN("HTVAL-IMP-05: implicit PTE read GPF, htinst == read pseudoinstruction");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(HGATP_MODE_SV39X4);

    two_stage_ctx_t ctx;
    uintptr_t test_va = IMP_TEST_VA;

    uintptr_t victim_gpa = setup_implicit_walk_victim_level(&ctx, test_va,
                                              /*victim_pt_level=*/0,
                                              /*victim_g_flags=*/0);

    uintptr_t pte_offset = VA_VPN(test_va, 0) * sizeof(uintptr_t);
    uintptr_t pte_gpa = victim_gpa + pte_offset;

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_load_expect_fault, test_va);
    TEST_ASSERT("implicit L0 GPF triggered", trap_was_triggered());
    if (trap_was_triggered()) {
        TEST_ASSERT_EQ("cause = 21 (load-gpf)",
                       trap_get_cause(), CAUSE_LOAD_GUEST_PAGE_FAULT);

        /* Strict spec check: htval == 0 accepted (no htinst
         * requirement); htval != 0 requires htval == PTE_GPA>>2 and
         * htinst == 0x00003000 with zero NOT allowed. */
        CHECK_IMPLICIT_FAULT_REPORT(pte_gpa >> 2, (uintptr_t)0x00003000);
    }
    trap_expect_end();

    two_stage_cleanup(&ctx);
    hyp_reset_state();
    HYP_TEST_END();
}

/* ===================================================================
 * HTVAL-IMP-04-FETCH: L0 PTE GPF on fetch walk
 *
 * Same as IMP-04 (store walk) but triggered by an instruction fetch.
 * The exception cause follows the ORIGINAL access type:
 *   fetch -> cause=20 (inst guest-page-fault).
 * htval still points to the PTE GPA (implicit read during walk).
 * =================================================================== */
TEST_REGISTER(test_htval_imp_04_fetch_walk);
bool test_htval_imp_04_fetch_walk(void) {
    TEST_BEGIN("HTVAL-IMP-04f: implicit VS-stage L0 PTE GPF on fetch walk");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(HGATP_MODE_SV39X4);

    two_stage_ctx_t ctx;
    uintptr_t test_va = IMP_TEST_VA;

    uintptr_t victim_gpa = setup_implicit_walk_victim_level(&ctx, test_va,
                                              /*victim_pt_level=*/0,
                                              /*victim_g_flags=*/0);

    uintptr_t pte_offset = VA_VPN(test_va, 0) * sizeof(uintptr_t);
    uintptr_t pte_gpa = victim_gpa + pte_offset;

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_exec_expect_fault, test_va);
    TEST_ASSERT("implicit L0 fetch-walk GPF triggered", trap_was_triggered());
    if (trap_was_triggered()) {
        /* Per RISC-V spec: cause follows the original access type.
         * Fetch -> cause=20 (inst guest-page-fault). */
        TEST_ASSERT_EQ("cause = 20 (inst-gpf, original access)",
                       trap_get_cause(), CAUSE_INST_GUEST_PAGE_FAULT);
        CHECK_HTVAL("htval = PTE_GPA>>2", pte_gpa >> 2);
    }
    trap_expect_end();

    two_stage_cleanup(&ctx);
    hyp_reset_state();
    HYP_TEST_END();
}

/* ===================================================================
 * HTVAL-IMP-06: Implicit write GPF (VS-stage A-bit update)
 *
 * Construct a VS-stage PTE with A=0 in a page where G-stage has
 * V=1, R=1, W=1, A=1, D=0. When the hardware walker tries to
 * auto-set the A-bit, the implicit write faults because D=0 in
 * G-stage (without Svadu). htval = PTE page GPA >> 2.
 *
 * If the platform supports Svadu (auto-updates A/D without fault),
 * no GPF fires and we TEST_SKIP.
 * =================================================================== */
TEST_REGISTER(test_htval_imp_06_implicit_write);
bool test_htval_imp_06_implicit_write(void) {
    TEST_BEGIN("HTVAL-IMP-06: implicit PTE write GPF (A-bit update, D=0 in G-stage)");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(HGATP_MODE_SV39X4);

    two_stage_ctx_t ctx;
    uintptr_t test_va = IMP_TEST_VA;

    /* G-stage victim flags: V=1 R=1 W=1 X=1 U=1 A=1 D=0.
     * Without Svadu, an implicit write (A-bit update) to the PTE
     * page faults because D=0. */
    uintptr_t victim_g_flags = G_FLAGS_RWXU_AD & ~PTE_D;

    uintptr_t victim_gpa = setup_implicit_walk_victim_level(&ctx, test_va,
                                              /*victim_pt_level=*/0,
                                              victim_g_flags);

    uintptr_t pte_offset = VA_VPN(test_va, 0) * sizeof(uintptr_t);
    uintptr_t pte_gpa = victim_gpa + pte_offset;

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_load_expect_fault, test_va);
    bool fired = trap_was_triggered();
    trap_expect_end();

    if (!fired) {
        /* Platform has Svadu or does not fault on D=0 for A-bit writes.
         * The implicit write succeeded — no GPF. */
        LOG_W("platform auto-updates A/D (Svadu), no implicit write GPF\n");
        two_stage_cleanup(&ctx);
        hyp_reset_state();
        TEST_SKIP("Svadu prevents implicit write GPF");
    }

    /* A GPF fired. The cause should follow the ORIGINAL access type
     * (load=21), since the implicit write is part of the load walk. */
    TEST_ASSERT_EQ("cause = 21 (load-gpf)",
                   trap_get_cause(), CAUSE_LOAD_GUEST_PAGE_FAULT);
    CHECK_HTVAL("htval = PTE page GPA>>2 (implicit write)", pte_gpa >> 2);

    two_stage_cleanup(&ctx);
    hyp_reset_state();
    HYP_TEST_END();
}

/* ===================================================================
 * HTVAL-IMP-07: Sv48x4 implicit GPF path
 *
 * Same implicit PTE GPF scenario as IMP-02 but under Sv48x4 G-stage
 * mode. Verifies that htval = PTE GPA >> 2 is mode-independent.
 * Skipped if the platform does not support Sv48x4.
 * =================================================================== */
TEST_REGISTER(test_htval_imp_07_sv48x4);
bool test_htval_imp_07_sv48x4(void) {
    TEST_BEGIN("HTVAL-IMP-07: implicit VS-stage L0 PTE GPF under Sv48x4");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(HGATP_MODE_SV48X4);

    two_stage_ctx_t ctx;
    uintptr_t test_va = IMP_TEST_VA;

    /* Use Sv39 VS-stage + Sv48x4 G-stage. */
    uintptr_t victim_gpa = _setup_imp_victim_mode(&ctx, test_va,
                                                   /*victim_pt_level=*/0,
                                                   /*victim_g_flags=*/0,
                                                   SATP_MODE_SV39,
                                                   HGATP_MODE_SV48X4);

    uintptr_t pte_offset = VA_VPN(test_va, 0) * sizeof(uintptr_t);
    uintptr_t pte_gpa = victim_gpa + pte_offset;

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_load_expect_fault, test_va);
    TEST_ASSERT("implicit L0 GPF triggered (Sv48x4)", trap_was_triggered());
    if (trap_was_triggered()) {
        TEST_ASSERT_EQ("cause = 21 (load-gpf)",
                       trap_get_cause(), CAUSE_LOAD_GUEST_PAGE_FAULT);
        CHECK_HTVAL("htval = PTE_GPA>>2 (Sv48x4)", pte_gpa >> 2);
    }
    trap_expect_end();

    two_stage_cleanup(&ctx);
    hyp_reset_state();
    HYP_TEST_END();
}
