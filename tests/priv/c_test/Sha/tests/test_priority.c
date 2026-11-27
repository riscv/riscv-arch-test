/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 6: Exception priority verification
 *
 * Spec anchors:
 *   norm:HSyncExcPrio — G-stage fault > VS-stage fault
 *   hypervisor.adoc:2043-2051 — G-stage check before VS-stage
 *
 * 2 tests: SHA-PRIO-01 ~ SHA-PRIO-02
 * =================================================================== */

/* VS-mode helper: perform a load from an address */
static uintptr_t _prio_vs_do_load(uintptr_t addr) {
    uintptr_t val;
    asm volatile ("ld %0, 0(%1)" : "=r"(val) : "r"(addr));
    return val;
}

/* VS-mode payload: jump to target address (X=0 page -> inst-fetch GPF).
 *
 * Uses the _exec_return_addr recovery pattern (same as
 * test_vs_exec_expect_fault / test_vs_jump_to) so the M-mode trap
 * handler can redirect mepc back to the recovery label after
 * capturing the fault, instead of advancing epc into the same
 * X=0 page and re-faulting forever. */
static uintptr_t _prio_vs_fetch_target(uintptr_t addr)
{
    extern uintptr_t _exec_return_addr __attribute__((unused));
    asm volatile (
        ".option push\n\t"
        ".option norvc\n\t"
        "la   t0, 1f\n\t"
        "la   t1, _exec_return_addr\n\t"
        "sd   t0, 0(t1)\n\t"
        "mv   ra, t0\n\t"
        "jr   %0\n\t"
        "1:\n\t"
        "sd   zero, 0(t1)\n\t"
        ".option pop\n\t"
        :: "r"(addr)
        : "t0", "t1", "ra", "memory"
    );
    return 0;
}

/* ---- SHA-PRIO-01: G-stage fault > VS-stage fault (load) ---- */

TEST_REGISTER(test_sha_prio_gstage_over_vsstage);
bool test_sha_prio_gstage_over_vsstage(void) {
    TEST_BEGIN("SHA-PRIO-01: G-stage fault takes priority over VS-stage fault");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t target_gpa = 0x50000000UL;

    gpt_pool_reset();
    two_stage_ctx_t ctx;
    two_stage_init(&ctx, SATP_MODE_BARE, SUITE_HGATP_MODE);

    uintptr_t base = PLATFORM_MEM_BASE & ~(PAGE_SIZE_2M - 1);
    two_stage_setup_identity(&ctx, base, PLATFORM_MEM_SIZE,
                             G_FLAGS_RWXU_AD, PT_LEVEL_2M);

    /* mie is M-level and the suite body runs in S(HS)-mode under the T-SBI
     * S-mode-normal boot, so go through the T-SBI CSR proxy. */
    uintptr_t saved_mie = tsbi_csr_read(CSR_MIE);
    tsbi_csr_clear(CSR_MIE, 1UL << 7);  /* clear MTIE */

    trap_expect_begin();
    two_stage_run_in_vs(&ctx, _prio_vs_do_load, target_gpa);
    bool fired = trap_was_triggered();
    uintptr_t cause = fired ? trap_get_cause() : 0;
    uintptr_t htval = fired ? trap_get_htval() : 0;
    trap_expect_end();

    tsbi_csr_write(CSR_MIE, saved_mie);
    two_stage_cleanup(&ctx);

    TEST_ASSERT("G-stage fault triggered", fired);
    if (fired) {
        TEST_ASSERT_EQ("cause == load guest-page-fault (21)",
                       cause, (uintptr_t)CAUSE_LOAD_GUEST_PAGE_FAULT);
        TEST_ASSERT_EQ("htval == target GPA >> 2",
                       htval, target_gpa >> 2);
        TEST_ASSERT("htval != 0 (Shtvala guarantee)", htval != 0);
    }

    HYP_TEST_END();
}

/* ---- SHA-PRIO-02: Inst-fetch G-stage fault > illegal-instruction ---- */

TEST_REGISTER(test_sha_prio_inst_fetch_over_illegal);
bool test_sha_prio_inst_fetch_over_illegal(void) {
    TEST_BEGIN("SHA-PRIO-02: inst-fetch GPF takes priority over illegal-inst");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    /* Spec: norm:HSyncExcPrio — guest-page-fault from G-stage has higher
     * priority than illegal-instruction exception.
     *
     * The G-stage translation check occurs during the instruction fetch
     * stage, before instruction decode. Therefore, if a G-stage page has
     * X=0, the fetch itself faults (cause=20) before the instruction can
     * be decoded — an illegal instruction at the same address would never
     * be detected. This test verifies that priority by mapping a page
     * with R+W+U but X=0 in G-stage and jumping to it from VS-mode.
     *
     * The GPF is not delegated (medeleg[20]=0), so it traps to M-mode.
     * The M-mode handler captures cause/htval and redirects mepc to the
     * _exec_return_addr recovery label set by _prio_vs_fetch_target,
     * escaping the X=0 page in one shot. */

    uintptr_t target_gpa = 0x50000000UL;

    gpt_pool_reset();
    two_stage_ctx_t ctx;
    two_stage_init(&ctx, SATP_MODE_BARE, SUITE_HGATP_MODE);

    uintptr_t base = PLATFORM_MEM_BASE & ~(PAGE_SIZE_2M - 1);
    two_stage_setup_identity(&ctx, base, PLATFORM_MEM_SIZE,
                             G_FLAGS_RWXU_AD, PT_LEVEL_2M);

    /* Map target GPA with R+W+U, NO X — triggers inst-fetch GPF.
     * The page is mapped (valid PTE) but lacks execute permission,
     * so the G-stage fetch check faults before instruction decode. */
    uintptr_t no_x_flags = PTE_V | PTE_R | PTE_W | PTE_U | PTE_A | PTE_D;
    two_stage_g_map_page(&ctx, target_gpa, target_gpa,
                         no_x_flags, PT_LEVEL_4K);

    /* Disable timer interrupts to protect armed flag. mie is M-level and the
     * suite body runs in S(HS)-mode under the T-SBI S-mode-normal boot, so go
     * through the T-SBI CSR proxy. */
    uintptr_t saved_mie = tsbi_csr_read(CSR_MIE);
    tsbi_csr_clear(CSR_MIE, 1UL << 7);  /* clear MTIE */

    /* Arm the M-mode trap mechanism */
    trap_expect_begin();

    /* Run in VS-mode: jalr to X=0 page -> inst-fetch GPF captured by
     * M-mode handler via _exec_return_addr recovery. */
    two_stage_run_in_vs(&ctx, _prio_vs_fetch_target, target_gpa);

    /* Read trap record */
    bool fired = trap_was_triggered();
    uintptr_t cause = fired ? trap_get_cause() : 0;
    uintptr_t htval = fired ? trap_get_htval() : 0;
    trap_expect_end();

    /* Restore state */
    tsbi_csr_write(CSR_MIE, saved_mie);

    two_stage_cleanup(&ctx);

    /* Verify: the inst-fetch GPF was captured by the M-mode handler */
    TEST_ASSERT("inst-fetch GPF triggered", fired);
    if (fired) {
        TEST_ASSERT_EQ("cause == inst guest-page-fault (20)",
                       cause, (uintptr_t)CAUSE_INST_GUEST_PAGE_FAULT);
        TEST_ASSERT_EQ("htval == target GPA >> 2",
                       htval, target_gpa >> 2);
        TEST_ASSERT("htval != 0 (Shtvala guarantee)", htval != 0);
    }

    HYP_TEST_END();
}
