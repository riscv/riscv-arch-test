/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * Group 7: htval not clobbered by non-GPF traps (HTVAL-CLR-*)
 *
 * Spec anchor:
 *   norm:H_htval — htval is written by the implementation only on
 *   guest-page-faults and certain hypervisor-load/store faults.
 *   Other exceptions MUST NOT modify htval (it is not implementation-
 *   defined for non-GPF causes — value is unchanged).
 *
 * Test list:
 *   HTVAL-CLR-01  illegal-instruction in M-mode does not write htval
 *   HTVAL-CLR-02  write to a read-only CSR in M-mode does not write htval
 *   HTVAL-CLR-03  EBREAK in M-mode does not write htval
 *   HTVAL-CLR-04  misaligned load in M-mode does not write htval
 *
 * Strategy: pre-load htval with a sentinel, fire a non-GPF trap,
 * read htval back. The trap has to be taken into M-mode:
 * norm:htval_sz_acc_op has the implementation write htval on any trap
 * taken into HS-mode and norm:htval_trapval mandates zero for a non-GPF
 * one, so a stimulus fired from S(HS)-mode -- where the suite body runs
 * under the T-SBI S-mode-normal boot -- would legitimately clear the
 * sentinel. M-mode traps leave htval alone, and the trap framework
 * records cause/tval into trap_record without touching htval.
 * =================================================================== */

static inline void htval_seed(uintptr_t v) {
    asm volatile ("csrw " CSR_STR(CSR_HTVAL) ", %0" :: "r"(v));
}
static inline uintptr_t htval_peek(void) {
    uintptr_t v;
    asm volatile ("csrr %0, " CSR_STR(CSR_HTVAL) : "=r"(v));
    return v;
}

#define HTVAL_SENTINEL  0x1234567890ABCDEFUL

/* Non-GPF stimuli fired from M-mode (CLR-01..04). */
#define CLR_STIM_ILLEGAL  0   /* csrrw x0, 0x004, x0 - nonexistent CSR */
#define CLR_STIM_RO_CSR   1   /* csrrw x0, cycle, x0 - write to RO CSR */
#define CLR_STIM_EBREAK   2   /* ebreak                                */
#define CLR_STIM_MISALIGN 3   /* misaligned 8-byte load                */

static bool      g_clr_fired;
static uintptr_t g_clr_cause;
static uintptr_t g_clr_addr;

static uintptr_t _clr_m_stimulus(uintptr_t which) {
    trap_expect_begin();
    switch (which) {
    case CLR_STIM_ILLEGAL:
        /* 32-bit illegal CSR access (csrrw zero, 0x004, zero). The trap
         * handler advances mepc by 4 and we stay armed for exactly one trap.
         * A 16-bit c.unimp (0x0000) only advances by 2 and would re-fault on
         * the second halfword. */
        asm volatile (".option push\n\t"
                      ".option norvc\n\t"
                      ".4byte 0x00401073\n\t"
                      ".option pop");
        break;
    case CLR_STIM_RO_CSR:
        /* csrrw zero, cycle, zero (encoding 0xC0001073): write to the
         * read-only cycle CSR. Used instead of a plain `ecall` because the
         * framework's M-mode ecall path is reserved for privilege-switching
         * and T-SBI service requests, and never surfaces as a recorded trap. */
        asm volatile (".option push\n\t"
                      ".option norvc\n\t"
                      ".4byte 0xC0001073\n\t"
                      ".option pop");
        break;
    case CLR_STIM_EBREAK:
        asm volatile ("ebreak");
        break;
    default:
        asm volatile ("ld t0, 0(%0)" :: "r"(g_clr_addr) : "t0", "memory");
        break;
    }
    g_clr_fired = trap_was_triggered();
    g_clr_cause = g_clr_fired ? trap_get_cause() : 0;
    trap_expect_end();
    return 0;
}

/* Fire one non-GPF stimulus in M-mode and record whether it trapped. */
static void clr_fire_in_m(uintptr_t which) {
    g_clr_fired = false;
    g_clr_cause = 0;
    (void)run_in_priv(PRIV_M, _clr_m_stimulus, which);
}

TEST_REGISTER(test_htval_clr_01_illegal_inst);
bool test_htval_clr_01_illegal_inst(void) {
    TEST_BEGIN("HTVAL-CLR-01: illegal-instruction does not modify htval");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    htval_seed(HTVAL_SENTINEL);

    clr_fire_in_m(CLR_STIM_ILLEGAL);
    TEST_ASSERT("trap triggered", g_clr_fired);
    TEST_ASSERT_EQ("cause matches", g_clr_cause,
                   (uintptr_t)CAUSE_ILLEGAL_INST);
    TEST_ASSERT_EQ("htval preserved", htval_peek(), HTVAL_SENTINEL);

    htval_seed(0);
    HYP_TEST_END();
}

TEST_REGISTER(test_htval_clr_02_csr_ro_write);
bool test_htval_clr_02_csr_ro_write(void) {
    TEST_BEGIN("HTVAL-CLR-02: write to RO CSR (illegal-inst) does not modify htval");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    htval_seed(HTVAL_SENTINEL);

    /* csrrw zero, cycle, zero — write to read-only CSR cycle. The
     * encoding is 0xC0001073. We use this instead of a plain `ecall`
     * because the framework's M-mode ecall path is reserved for
     * privilege-switching and never surfaces as a recorded trap. */
    clr_fire_in_m(CLR_STIM_RO_CSR);
    TEST_ASSERT("trap triggered", g_clr_fired);
    TEST_ASSERT_EQ("cause matches", g_clr_cause,
                   (uintptr_t)CAUSE_ILLEGAL_INST);
    TEST_ASSERT_EQ("htval preserved", htval_peek(), HTVAL_SENTINEL);

    htval_seed(0);
    HYP_TEST_END();
}

TEST_REGISTER(test_htval_clr_03_ebreak);
bool test_htval_clr_03_ebreak(void) {
    TEST_BEGIN("HTVAL-CLR-03: EBREAK does not modify htval");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");

#ifdef SKIP_BREAKPOINT_TESTS
    TEST_SKIP("platform does not support breakpoint (SKIP_BREAKPOINT_TESTS)");
#endif

    htval_seed(HTVAL_SENTINEL);

    clr_fire_in_m(CLR_STIM_EBREAK);
    TEST_ASSERT("trap triggered", g_clr_fired);
    TEST_ASSERT_EQ("cause matches", g_clr_cause, (uintptr_t)CAUSE_BREAKPOINT);
    TEST_ASSERT_EQ("htval preserved", htval_peek(), HTVAL_SENTINEL);

    htval_seed(0);
    HYP_TEST_END();
}

TEST_REGISTER(test_htval_clr_04_misalign);
bool test_htval_clr_04_misalign(void) {
    TEST_BEGIN("HTVAL-CLR-04: load-misalign (no H walk) does not modify htval");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    htval_seed(HTVAL_SENTINEL);

    /* Try a misaligned 8B load on M-mode bare metal. The platform
     * may handle misalign in HW (no trap) — accept either outcome
     * but only assert htval if a trap actually fired. */
    g_clr_addr = (uintptr_t)((volatile uint8_t *)test_data_area + 1);

    clr_fire_in_m(CLR_STIM_MISALIGN);

    if (g_clr_fired) {
        LOG_D("trap fired, cause=%lu\n", (unsigned long)g_clr_cause);
    }
    TEST_ASSERT_EQ("htval preserved", htval_peek(), HTVAL_SENTINEL);

    htval_seed(0);
    HYP_TEST_END();
}

/* ===================================================================
 * Plan-style CLR tests (HTVAL-CLR-05 to HTVAL-CLR-08)
 *
 * Spec anchor:
 *   norm:htval_trapval — "For other traps, htval is set to zero"
 *
 * Strategy: trigger a real GPF via fire_vs_load_fault() so that
 * trap_get_htval() returns GPA>>2 (non-zero), then immediately
 * trigger a non-GPF trap from VS-mode. The M-mode trap handler
 * records htval=0 for non-GPF causes (matching the mtval2 behaviour),
 * confirming that htval/mtval2 is cleared after non-GPF traps.
 * =================================================================== */

extern uintptr_t ecall_args[2];

/* VS-mode helper: plain ecall (not a privilege-switch). */
static uintptr_t vs_plain_ecall_clr(uintptr_t arg) {
    (void)arg;
    ecall_args[0] = 0;  /* NOT ECALL_GOTO_PRIV */
    asm volatile ("ecall" ::: "memory");
    return 0;
}

TEST_REGISTER(test_htval_clr_05_gpf_then_ecall);
bool test_htval_clr_05_gpf_then_ecall(void) {
    TEST_BEGIN("HTVAL-CLR-05: htval=0 on VS ecall after GPF");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t target = (uintptr_t)test_fault_page;
    uintptr_t flags  = (G_FLAGS_RWXU_AD & ~PTE_R);

    /* Phase 1: trigger GPF to populate htval with GPA>>2. */
    bool gpf = fire_vs_load_fault(target, flags);
    TEST_ASSERT("GPF fired", gpf);
    TEST_ASSERT("htval != 0 after GPF", trap_get_htval() != 0);

    /* Phase 2: non-GPF ecall from VS-mode. */
    trap_expect_begin();
    (void)run_in_vs_mode(vs_plain_ecall_clr, 0);
    TEST_ASSERT("ecall trap fired", trap_was_triggered());
    trap_expect_end();

    TEST_ASSERT_EQ("cause = 10 (ecall-from-vs)",
                   trap_get_cause(), (uintptr_t)CAUSE_ECALL_FROM_VS);
    TEST_ASSERT_EQ("htval cleared after non-GPF",
                   trap_get_htval(), 0UL);

    hyp_reset_state();
    HYP_TEST_END();
}

/* VS-mode helper: illegal instruction (non-existent CSR 0x004). */
static uintptr_t vs_illegal_inst_clr(uintptr_t arg) {
    (void)arg;
    asm volatile (".option push\n\t"
                  ".option norvc\n\t"
                  ".4byte 0x00401073\n\t"   /* csrrw x0, 0x004, x0 */
                  ".option pop");
    return 0;
}

TEST_REGISTER(test_htval_clr_06_gpf_then_illegal);
bool test_htval_clr_06_gpf_then_illegal(void) {
    TEST_BEGIN("HTVAL-CLR-06: htval=0 on VS illegal-inst after GPF");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t target = (uintptr_t)test_fault_page;
    uintptr_t flags  = (G_FLAGS_RWXU_AD & ~PTE_R);

    bool gpf = fire_vs_load_fault(target, flags);
    TEST_ASSERT("GPF fired", gpf);
    TEST_ASSERT("htval != 0 after GPF", trap_get_htval() != 0);

    /* Route cause 2 back to HS-mode before phase 2: the T-SBI delegation
     * baseline also sets hedeleg[2], and a trap taken into VS-mode never
     * rewrites htval (norm:htval_sz_acc_op only covers traps taken into
     * HS-mode), which is exactly what this test measures. */
    setup_deleg_to_hs(1UL << CAUSE_ILLEGAL_INST);

    trap_expect_begin();
    (void)run_in_vs_mode(vs_illegal_inst_clr, 0);
    TEST_ASSERT("illegal-inst trap fired", trap_was_triggered());
    trap_expect_end();

    TEST_ASSERT_EQ("cause = 2 (illegal-inst)",
                   trap_get_cause(), (uintptr_t)CAUSE_ILLEGAL_INST);
    TEST_ASSERT_EQ("htval cleared after non-GPF",
                   trap_get_htval(), 0UL);

    hyp_reset_state();
    HYP_TEST_END();
}

TEST_REGISTER(test_htval_clr_07_gpf_then_pagefault);
bool test_htval_clr_07_gpf_then_pagefault(void) {
    TEST_BEGIN("HTVAL-CLR-07: htval=0 on VS page-fault after GPF");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t target = (uintptr_t)test_fault_page;
    uintptr_t flags  = (G_FLAGS_RWXU_AD & ~PTE_R);

    /* Phase 1: GPF */
    bool gpf = fire_vs_load_fault(target, flags);
    TEST_ASSERT("GPF fired", gpf);
    TEST_ASSERT("htval != 0 after GPF", trap_get_htval() != 0);

    /* Phase 2: VS-stage page fault.
     * vsatp=Sv39 maps kernel only; hgatp=Sv39x4 maps everything.
     * Load from test_fault_page triggers VS-stage page fault
     * (cause=13) because it is NOT in VS-stage mapping. */
    two_stage_ctx_t ctx;
    gpt_pool_reset();
    two_stage_init(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    uintptr_t lo_base  = PLATFORM_MEM_BASE & ~(PAGE_SIZE_2M - 1);
    uintptr_t r_start  = (uintptr_t)__vm_test_region_start;
    uintptr_t lo_end   = r_start & ~(PAGE_SIZE_2M - 1);
    uintptr_t r_end    = (uintptr_t)__vm_test_region_end;
    uintptr_t vs_flags = PTE_V | PTE_R | PTE_W | PTE_X | PTE_A | PTE_D;

    /* VS-stage: kernel at 2MB (test region NOT mapped). */
    two_stage_vs_identity(&ctx, lo_base, lo_end - lo_base,
                          vs_flags, PT_LEVEL_2M);

    /* G-stage: kernel + test region fully mapped. */
    two_stage_setup_identity(&ctx, lo_base, lo_end - lo_base,
                             G_FLAGS_RWXU_AD, PT_LEVEL_2M);
    two_stage_setup_identity(&ctx, r_start, r_end - r_start,
                             G_FLAGS_RWXU_AD, PT_LEVEL_4K);

    /* Route cause 13 back to HS-mode for the same reason as CLR-06: the
     * delegation baseline delegates load page-faults to VS, and only a trap
     * taken into HS-mode rewrites htval. */
    setup_deleg_to_hs(1UL << CAUSE_LOAD_PAGE_FAULT);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, test_vs_load_expect_fault, target);
    TEST_ASSERT("page-fault trap fired", trap_was_triggered());
    trap_expect_end();

    TEST_ASSERT_EQ("cause = 13 (load-page-fault)",
                   trap_get_cause(), (uintptr_t)CAUSE_LOAD_PAGE_FAULT);
    TEST_ASSERT_EQ("htval cleared after non-GPF",
                   trap_get_htval(), 0UL);

    two_stage_cleanup(&ctx);
    hyp_reset_state();
    HYP_TEST_END();
}

/* VS-mode helper: read HS-level CSR hstatus -> virtual-instruction. */
static uintptr_t vs_csrr_hstatus_clr(uintptr_t arg) {
    (void)arg;
    uintptr_t v;
    asm volatile ("csrr %0, " CSR_STR(CSR_HSTATUS) : "=r"(v));   /* hstatus */
    return v;
}

TEST_REGISTER(test_htval_clr_08_gpf_then_virtual_inst);
bool test_htval_clr_08_gpf_then_virtual_inst(void) {
    TEST_BEGIN("HTVAL-CLR-08: htval=0 on virtual-instruction after GPF");
    if (!SHTVALA_AVAILABLE) TEST_SKIP("Shtvala extension not available");
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t target = (uintptr_t)test_fault_page;
    uintptr_t flags  = (G_FLAGS_RWXU_AD & ~PTE_R);

    bool gpf = fire_vs_load_fault(target, flags);
    TEST_ASSERT("GPF fired", gpf);
    TEST_ASSERT("htval != 0 after GPF", trap_get_htval() != 0);

    trap_expect_begin();
    (void)run_in_vs_mode(vs_csrr_hstatus_clr, 0);
    TEST_ASSERT("virtual-inst trap fired", trap_was_triggered());
    trap_expect_end();

    TEST_ASSERT_EQ("cause = 22 (virtual-instruction)",
                   trap_get_cause(), (uintptr_t)CAUSE_VIRTUAL_INSTRUCTION);
    TEST_ASSERT_EQ("htval cleared after non-GPF",
                   trap_get_htval(), 0UL);

    hyp_reset_state();
    HYP_TEST_END();
}
