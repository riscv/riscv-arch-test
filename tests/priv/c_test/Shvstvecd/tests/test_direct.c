/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_direct.c - Group 3: MODE=Direct VS-mode trap dispatch
 *
 * Per SPEC/supervisor.adoc:355-364 and Shvstvecd Direct-mode invariant:
 *   When vstvec.MODE=Direct, every trap (sync exception OR async
 *   interrupt) sets pc to BASE -- NOT to BASE + 4*cause.
 *
 * These tests enter VS-mode via run_in_vs_mode() or run_in_vu_mode(),
 * set up vstvec (via stvec instruction in V=1) to point at
 * shvstvecd_trap_entry, trigger a trap delegated to VS-mode, then
 * verify the landing address.
 *
 * Test coverage:
 *   VSTVEC-DIR-01: ecall from VU-mode (cause=8)
 *   VSTVEC-DIR-02: illegal instruction (cause=2)
 *   VSTVEC-INT-01: VSSIP interrupt lands at BASE (not BASE+4*cause)
 *   VSTVEC-DIR-03: load page-fault (cause=13) via two-stage
 */

/* ===================================================================
 * VS-mode payload functions
 * =================================================================== */

/* VSTVEC-DIR-01: VU-mode ecall payload.
 * In VU-mode, simply execute ecall. The framework enters VU-mode via
 * sret from VS-mode. ecall generates cause=8 (ecall from VU-mode).
 * With hedeleg bit 8 set, it is delegated to VS-mode. */
static uintptr_t vumode_exec_ecall(uintptr_t arg) {
    (void)arg;
    asm volatile ("ecall");
    return 0;
}

/* VSTVEC-DIR-02: VS-mode illegal instruction payload.
 * Sets vstvec via stvec (V=1), arms vsscratch, then executes an
 * illegal instruction (cause=2). */
static uintptr_t vsmode_trigger_illegal(uintptr_t entry) {
    /* V=1: csrw stvec actually writes vstvec; MODE=0 (Direct) */
    asm volatile ("csrw stvec, %0" :: "r"(entry));
    /* Arm vsscratch via sscratch (V=1) for the trap handler. */
    asm volatile ("csrw sscratch, %0"
                  :: "r"(shvstvecd_trap_scratch) : "memory");
    /* Trigger illegal instruction (cause=2). .4byte 0 is guaranteed
     * illegal on RV64. Trap entry advances sepc by 4. */
    asm volatile (".4byte 0x00000000");
    return 0;
}

/* VSTVEC-INT-01: VSSIP interrupt payload.
 * Sets vstvec, arms vsscratch, enables SSIE + SIE. */
static uintptr_t vsmode_enable_vssi_and_wait(uintptr_t entry) {
    /* V=1: csrw stvec actually writes vstvec; MODE=0 (Direct) */
    asm volatile ("csrw stvec, %0" :: "r"(entry));
    /* Arm vsscratch for the trap handler. */
    asm volatile ("csrw sscratch, %0"
                  :: "r"(shvstvecd_trap_scratch) : "memory");
    /* Enable SSIE (V=1: actually vsie.SSIE) */
    asm volatile ("csrs sie, %0" :: "r"(BIT_SSI));
    /* Enable SIE (V=1: actually vsstatus.SIE) — interrupt fires immediately */
    asm volatile ("csrs sstatus, %0" :: "r"(SSTATUS_SIE_BIT));
    /* VSSIP should have been taken by now; the nop gives a safe boundary. */
    asm volatile ("nop");
    /* Disable interrupts for tidiness before returning. */
    asm volatile ("csrc sstatus, %0" :: "r"(SSTATUS_SIE_BIT));
    asm volatile ("csrc sie, %0" :: "r"(BIT_SSI));
    return 0;
}

/* VSTVEC-DIR-03: load page-fault payload.
 * Runs in VS-mode with two-stage translation active. Loads from an
 * unmapped VS-stage VA, triggering load page-fault (cause=13). */
static uintptr_t vsmode_load_unmapped(uintptr_t addr) {
    volatile uint64_t *p = (volatile uint64_t *)addr;
    (void)*p;  /* triggers load page-fault; handler skips this insn */
    return 0;
}

/* ===================================================================
 * Test cases
 * =================================================================== */

/* VSTVEC-DIR-01: ecall from VU-mode (cause=8) lands at vstvec.BASE.
 *
 * Flow:
 *   1. HS-mode: delegate ecall-from-VU (cause=8) to VS via hedeleg.
 *   2. HS-mode: set vstvec to shvstvecd_trap_entry (Direct, MODE=0).
 *   3. HS-mode: arm vsscratch.
 *   4. Enter VU-mode via the one-way goto_priv().
 *   5. VU-mode: ecall -> hedeleg delegates to VS-mode.
 *   6. VS-mode handler at vstvec.BASE records trap_pc and vscause.
 *   7. Handler forces vsstatus.SPP=1 and sret -> resumes in VS-mode.
 *   8. goto_priv(PRIV_S): ecall-from-VS (cause=10) -> back to HS-mode. */
TEST_REGISTER(test_shvstvecd_dir_01_ecall_vu);
bool test_shvstvecd_dir_01_ecall_vu(void) {
    TEST_BEGIN("VSTVEC-DIR-01: Direct mode, VU ecall lands at vstvec.BASE");

    uintptr_t entry = (uintptr_t)&shvstvecd_trap_entry;
    TEST_ASSERT("entry is 4-byte aligned", (entry & 0x3UL) == 0);

    /* Delegate ecall-from-VU (cause=8) to VS-mode */
    hyp_delegate_to_vs(1UL << 8, 0);

    /* Set vstvec to Direct mode entry (from M-mode, CSR 0x205) */
    vstvec_write(entry);

    shvstvecd_reset_trap_record();

    /* Enter VU-mode and execute ecall (cause=8).
     *
     * goto_priv() is used instead of run_in_vu_mode(): the latter clears
     * hedeleg[8] before its mret so that its own VU trampoline's return ecall
     * can reach M-mode, which erases the hedeleg[8]=1 delegation this test is
     * about to observe. goto_priv(PRIV_VU) raises to M via an ecall-from-S
     * (cause 9) and leaves hedeleg untouched, so the stimulus ecall really is
     * delegated to VS. shvstvecd_trap_entry forces vsstatus.SPP=1 before its
     * sret, so execution resumes in VS-mode and the trailing goto_priv(PRIV_S)
     * (ecall-from-VS, cause 10) gets back to HS-mode. */
    goto_priv(PRIV_VU);
    (void)vumode_exec_ecall(0);
    goto_priv(PRIV_S);

    /* Direct mode: trap landing address must == BASE */
    TEST_ASSERT("trap PC equals vstvec.BASE",
                g_shvstvecd_trap_pc == entry);
    TEST_ASSERT("vscause == 8 (ecall from VU-mode)",
                shvstvecd_cause_code(g_shvstvecd_trap_cause) == 8);
    TEST_ASSERT("vscause is sync exception",
                !shvstvecd_is_interrupt(g_shvstvecd_trap_cause));

    hyp_undelegate();
    HYP_TEST_END();
}

/* VSTVEC-DIR-02: illegal instruction (cause=2) lands at vstvec.BASE. */
TEST_REGISTER(test_shvstvecd_dir_02_illegal_insn);
bool test_shvstvecd_dir_02_illegal_insn(void) {
    TEST_BEGIN("VSTVEC-DIR-02: Direct mode, illegal insn lands at vstvec.BASE");

    uintptr_t entry = (uintptr_t)&shvstvecd_trap_entry;
    TEST_ASSERT("entry is 4-byte aligned", (entry & 0x3UL) == 0);

    /* Delegate illegal-instruction (cause=2) to VS-mode */
    hyp_delegate_to_vs(1UL << 2, 0);

    shvstvecd_reset_trap_record();

    /* Enter VS-mode: set vstvec and trigger illegal insn */
    run_in_vs_mode(vsmode_trigger_illegal, entry);

    /* Direct mode: trap landing address must == BASE */
    TEST_ASSERT("trap PC equals vstvec.BASE",
                g_shvstvecd_trap_pc == entry);
    TEST_ASSERT("vscause == 2 (illegal instruction)",
                shvstvecd_cause_code(g_shvstvecd_trap_cause) == 2);
    TEST_ASSERT("vscause is sync exception",
                !shvstvecd_is_interrupt(g_shvstvecd_trap_cause));

    hyp_undelegate();
    HYP_TEST_END();
}

/* VSTVEC-INT-01: VSSIP interrupt lands at BASE (not BASE+4*cause).
 * Uses hvip to inject VSSIP, then enters VS-mode where we enable
 * the interrupt. Since MODE=Direct, trap should land at BASE. */
TEST_REGISTER(test_shvstvecd_int_01_vssip);
bool test_shvstvecd_int_01_vssip(void) {
    TEST_BEGIN("VSTVEC-INT-01: Direct mode, VSSIP lands at BASE (not BASE+offset)");

    uintptr_t entry = (uintptr_t)&shvstvecd_trap_entry;

    /* Delegate VSSIP (bit 2 in hideleg) to VS-mode */
    hyp_delegate_to_vs(0, 1UL << 2);

    shvstvecd_reset_trap_record();

    /* Inject VSSIP pending via hvip */
    hvip_set_vssi(true);

    /* Enter VS-mode: set vstvec and enable interrupt */
    run_in_vs_mode(vsmode_enable_vssi_and_wait, entry);

    /* Direct mode: interrupt also lands at BASE, NOT BASE + 4*cause. */
    TEST_ASSERT("trap PC equals BASE (Direct, not Vectored)",
                g_shvstvecd_trap_pc == entry);
    /* vscause: interrupt bit set, code = 1 (supervisor software interrupt) */
    TEST_ASSERT("vscause is interrupt",
                shvstvecd_is_interrupt(g_shvstvecd_trap_cause));
    TEST_ASSERT("vscause code == 1 (VSSI)",
                shvstvecd_cause_code(g_shvstvecd_trap_cause) == 1);

    /* Cleanup */
    hvip_set_vssi(false);
    hyp_undelegate();
    HYP_TEST_END();
}

/* VSTVEC-DIR-03: load page-fault (cause=13) lands at vstvec.BASE.
 *
 * Uses two-stage translation: VS-stage Sv39 identity-maps kernel
 * region only; UNMAPPED_VA_1 is NOT mapped. G-stage identity-maps
 * everything. Load from UNMAPPED_VA_1 triggers VS-stage load
 * page-fault (cause=13), delegated to VS-mode via hedeleg. */
TEST_REGISTER(test_shvstvecd_dir_03_load_page_fault);
bool test_shvstvecd_dir_03_load_page_fault(void) {
    TEST_BEGIN("VSTVEC-DIR-03: Direct mode, load page-fault lands at BASE");

    uintptr_t entry = (uintptr_t)&shvstvecd_trap_entry;
    TEST_ASSERT("entry is 4-byte aligned", (entry & 0x3UL) == 0);

    /* Delegate load page-fault (cause=13) to VS-mode */
    hyp_delegate_to_vs(1UL << 13, 0);

    /* Set vstvec to Direct mode entry from M-mode */
    vstvec_write(entry);

    shvstvecd_reset_trap_record();

    /* Setup two-stage: VS-stage Sv39 with identity map for code only;
     * UNMAPPED_VA_1 deliberately NOT mapped. G-stage identity. */
    two_stage_ctx_t ctx;
    ts2_setup_full(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    /* Execute in VS-mode: load from UNMAPPED_VA_1 -> page-fault */
    two_stage_run_in_vs(&ctx, vsmode_load_unmapped, UNMAPPED_VA_1);

    /* Direct mode: trap landing address must == BASE */
    TEST_ASSERT("trap PC equals vstvec.BASE",
                g_shvstvecd_trap_pc == entry);
    TEST_ASSERT("vscause == 13 (load page-fault)",
                shvstvecd_cause_code(g_shvstvecd_trap_cause) == 13);
    TEST_ASSERT("vscause is sync exception",
                !shvstvecd_is_interrupt(g_shvstvecd_trap_cause));

    two_stage_cleanup(&ctx);
    hyp_undelegate();
    HYP_TEST_END();
}
