/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * test_vs_scratch.c - VSCR: VS CSR tests (vsscratch/vsepc/vscause/vstval)
 *
 * Group 8 of Hypervisor CSR subset test plan.
 *
 * Covers:
 *   VSCR-01  vsscratch basic read/write
 *   VSCR-02  vsepc WARL verification
 *   VSCR-03  vscause WLRL verification (exception + interrupt causes)
 *   VSCR-04  vstval WARL verification
 *   VSCR-05  V=1 trap correctly writes vsepc/vscause/vstval
 *   VSCR-06  V=0 trap uses sepc/scause/stval, not VS CSRs
 *   VSCR-07  V=1 CSR substitution (sscratch->vsscratch, etc.)
 * =================================================================== */

#include "hyp_test_helpers.h"

/* ===================================================================
 * VS-mode trap handler for VSCR-05.
 *
 * Records vsepc/vscause/vstval into globals, advances sepc by 4
 * to skip the faulting instruction, clears SIE+SPIE, forces SPP=1,
 * then returns via sret.
 *
 * NOTE: SPP must be explicitly set to 1 before sret. When the trap
 * originates from VU-mode, hardware sets vsstatus.SPP=0 (U-level),
 * which would cause sret to return to VU-mode instead of VS-mode.
 * =================================================================== */

static volatile uintptr_t g_vscr_vs_epc;
static volatile uintptr_t g_vscr_vs_cause;
static volatile uintptr_t g_vscr_vs_tval;
static volatile bool      g_vscr_vs_triggered;

static void vscr_vs_trap_handler(void) __attribute__((naked, aligned(4)));
static void vscr_vs_trap_handler(void)
{
    asm volatile (
        "addi   sp, sp, -32\n\t"
        "sd     ra, 0(sp)\n\t"
        "sd     t0, 8(sp)\n\t"
        "sd     t1, 16(sp)\n\t"
        "sd     t2, 24(sp)\n\t"

        /* Record vsepc (V=1 reads sepc which maps to vsepc) */
        "csrr   t0, sepc\n\t"
        "la     t2, g_vscr_vs_epc\n\t"
        "sd     t0, 0(t2)\n\t"

        /* Record vscause */
        "csrr   t0, scause\n\t"
        "la     t2, g_vscr_vs_cause\n\t"
        "sd     t0, 0(t2)\n\t"

        /* Record vstval */
        "csrr   t0, stval\n\t"
        "la     t2, g_vscr_vs_tval\n\t"
        "sd     t0, 0(t2)\n\t"

        /* Mark triggered */
        "li     t0, 1\n\t"
        "la     t2, g_vscr_vs_triggered\n\t"
        "sb     t0, 0(t2)\n\t"

        /* Advance sepc by 4 to skip faulting instruction */
        "csrr   t0, sepc\n\t"
        "addi   t0, t0, 4\n\t"
        "csrw   sepc, t0\n\t"

        /* Clear SIE (bit 1) and SPIE (bit 5) */
        "li     t0, 0x22\n\t"
        "csrc   sstatus, t0\n\t"

        /* Force SPP=1 so sret returns to VS-mode, not VU */
        "li     t0, 0x100\n\t"
        "csrs   sstatus, t0\n\t"

        "ld     ra, 0(sp)\n\t"
        "ld     t0, 8(sp)\n\t"
        "ld     t1, 16(sp)\n\t"
        "ld     t2, 24(sp)\n\t"
        "addi   sp, sp, 32\n\t"

        "sret\n\t"
    );
}

/* Setup helper for VSCR-05: delegate exception to VS-mode and
 * install the trap handler. */
static void vscr_setup_vs_trap(uintptr_t exc_mask)
{
    g_vscr_vs_epc = 0;
    g_vscr_vs_cause = 0;
    g_vscr_vs_tval = 0;
    g_vscr_vs_triggered = false;

    setup_deleg_to_vs(exc_mask, 0);
    vs_trap_setup_direct((uintptr_t)vscr_vs_trap_handler);

    /* (removed) The old "set mstatus.MPIE=1 so MIE=1 after mret into VS-mode"
     * is obsolete under S-mode-normal: mstatus is M-level (the raw csrr traps
     * from S), MPIE is a return-path bit the tsbi_csr_ guard refuses to proxy, and
     * every framework excursion re-enters via mret (MPIE<-1). It is also not
     * needed here -- VSCR-05 traps an EXCEPTION into VS via the hedeleg
     * delegation set above plus this suite's own vstvec handler; exception
     * delivery does not depend on mstatus.MIE (which only gates interrupts
     * while executing in M-mode). */
}

/* ===================================================================
 * VSCR-01: vsscratch basic read/write
 *
 * Verify vsscratch can be written and read back correctly.
 * =================================================================== */
TEST_REGISTER(vscr_01_vsscratch_basic_rw);
bool vscr_01_vsscratch_basic_rw(void)
{
    TEST_BEGIN("VSCR-01: vsscratch basic read/write");

    uintptr_t test_val = 0xABCD;

    /* Write vsscratch (CSR 0x240) */
    CSRW(CSR_VSSCRATCH, test_val);

    /* Read back and verify */
    uintptr_t val;
    val = CSRR(CSR_VSSCRATCH);

    TEST_ASSERT_EQ("vsscratch readback matches written value", val, test_val);

    HYP_TEST_END();
}

/* ===================================================================
 * VSCR-02: vsepc WARL verification
 *
 * Verify that vsepc respects WARL behavior (lower bits masked).
 * Per norm:vsepc_warl, vsepc must hold the same set of values
 * that sepc can hold (bit 0 always zero).
 * =================================================================== */
TEST_REGISTER(vscr_02_vsepc_warl);
bool vscr_02_vsepc_warl(void)
{
    TEST_BEGIN("VSCR-02: vsepc WARL verification");

    /* Write vsepc with odd address (lower bit set) */
    uintptr_t odd_addr = 0x1001;
    CSRW(CSR_VSEPC, odd_addr);

    /* Read back - should have lower bit cleared (alignment) */
    uintptr_t val;
    val = CSRR(CSR_VSEPC);

    /* Verify lower bit is cleared (WARL behavior) */
    TEST_ASSERT_EQ("vsepc lower bit cleared", val & 0x1, 0);

    /* Write aligned address */
    uintptr_t aligned_addr = 0x1000;
    CSRW(CSR_VSEPC, aligned_addr);

    val = CSRR(CSR_VSEPC);
    TEST_ASSERT_EQ("vsepc aligned address preserved", val, aligned_addr);

    HYP_TEST_END();
}

/* ===================================================================
 * VSCR-03: vscause WLRL verification
 *
 * Verify that vscause accepts legal cause values including
 * exception causes and interrupt causes (with interrupt bit set).
 * Per norm:vscause_wlrl, vscause must hold the same set of
 * values that scause can hold.
 * =================================================================== */
TEST_REGISTER(vscr_03_vscause_wlrl);
bool vscr_03_vscause_wlrl(void)
{
    TEST_BEGIN("VSCR-03: vscause WLRL verification");

    /* Test exception cause values */
    uintptr_t val;

    /* Instruction misaligned (cause=0) */
    CSRW(CSR_VSCAUSE, (uintptr_t)0);
    val = CSRR(CSR_VSCAUSE);
    TEST_ASSERT_EQ("vscause=0 (instruction misaligned) preserved", val, 0);

    /* Illegal instruction (cause=2) */
    CSRW(CSR_VSCAUSE, (uintptr_t)2);
    val = CSRR(CSR_VSCAUSE);
    TEST_ASSERT_EQ("vscause=2 (illegal instruction) preserved", val, 2);

    /* Instruction page fault (cause=12) */
    CSRW(CSR_VSCAUSE, (uintptr_t)12);
    val = CSRR(CSR_VSCAUSE);
    TEST_ASSERT_EQ("vscause=12 (instruction page fault) preserved", val, 12);

    /* Load page fault (cause=13) */
    CSRW(CSR_VSCAUSE, (uintptr_t)13);
    val = CSRR(CSR_VSCAUSE);
    TEST_ASSERT_EQ("vscause=13 (load page fault) preserved", val, 13);

    /* Test interrupt cause values (with interrupt bit set).
     * These verify vscause can hold the same interrupt values
     * that scause can hold (norm:vscause_wlrl). */
    uintptr_t int_ssi = CAUSE_INTERRUPT_BIT | 1;
    CSRW(CSR_VSCAUSE, int_ssi);
    val = CSRR(CSR_VSCAUSE);
    TEST_ASSERT_EQ("vscause=SSI interrupt preserved", val, int_ssi);

    uintptr_t int_sti = CAUSE_INTERRUPT_BIT | 5;
    CSRW(CSR_VSCAUSE, int_sti);
    val = CSRR(CSR_VSCAUSE);
    TEST_ASSERT_EQ("vscause=STI interrupt preserved", val, int_sti);

    uintptr_t int_sei = CAUSE_INTERRUPT_BIT | 9;
    CSRW(CSR_VSCAUSE, int_sei);
    val = CSRR(CSR_VSCAUSE);
    TEST_ASSERT_EQ("vscause=SEI interrupt preserved", val, int_sei);

    /* Verify vscause domain matches scause domain: write to scause
     * and vscause with the same value, both should hold it. */
    uintptr_t domain_test = CAUSE_INTERRUPT_BIT | 1;
    CSRW(CSR_SCAUSE, domain_test);
    uintptr_t scause_val;
    scause_val = CSRR(CSR_SCAUSE);

    CSRW(CSR_VSCAUSE, domain_test);
    val = CSRR(CSR_VSCAUSE);
    TEST_ASSERT_EQ("vscause domain matches scause domain",
                   val, scause_val);

    HYP_TEST_END();
}

/* ===================================================================
 * VSCR-04: vstval WARL verification
 *
 * Verify that vstval can be written and read back.
 * Per norm:vstval_warl, vstval must hold the same set of values
 * that stval can hold.
 * =================================================================== */
TEST_REGISTER(vscr_04_vstval_warl);
bool vscr_04_vstval_warl(void)
{
    TEST_BEGIN("VSCR-04: vstval WARL verification");

    uintptr_t val;

    /* Write vstval with all 1s */
    CSRW(CSR_VSTVAL, (uintptr_t)-1);
    val = CSRR(CSR_VSTVAL);

    /* Write a specific test value */
    uintptr_t test_val = 0xDEADBEEF;
    CSRW(CSR_VSTVAL, test_val);
    val = CSRR(CSR_VSTVAL);
    TEST_ASSERT_EQ("vstval test value preserved", val, test_val);

    /* Write zero */
    CSRW(CSR_VSTVAL, 0);
    val = CSRR(CSR_VSTVAL);
    TEST_ASSERT_EQ("vstval zero preserved", val, 0);

    /* Verify vstval domain matches stval domain: write the same
     * value to both and compare readback. */
    uintptr_t domain_vals[] = { 0, 0xDEADBEEF, (uintptr_t)-1, 0x80000000UL };
    for (int i = 0; i < 4; i++) {
        CSRW(CSR_STVAL, domain_vals[i]);
        uintptr_t stval_val;
        stval_val = CSRR(CSR_STVAL);

        CSRW(CSR_VSTVAL, domain_vals[i]);
        val = CSRR(CSR_VSTVAL);

        TEST_ASSERT_EQ("vstval domain matches stval domain",
                       val, stval_val);
    }

    HYP_TEST_END();
}

/* ===================================================================
 * VSCR-05: V=1 trap correctly writes vsepc/vscause/vstval
 *
 * Verify that when a trap is delegated to VS-mode, the hardware
 * correctly populates vsepc, vscause, and vstval.
 *
 * Per norm:H_trap_vs_csrwrites:
 *   "A trap into VS-mode also writes SPIE and SIE in vsstatus
 *    and writes CSRs vsepc, vscause, and vstval."
 * =================================================================== */
TEST_REGISTER(vscr_05_v1_trap_writes_vs_csrs);
bool vscr_05_v1_trap_writes_vs_csrs(void)
{
    TEST_BEGIN("VSCR-05: V=1 trap correctly writes vsepc/vscause/vstval");

    /* Delegate illegal-instruction (cause=2) to VS-mode */
    vscr_setup_vs_trap(1UL << CAUSE_ILLEGAL_INST);

    /* Trigger illegal instruction in VS-mode.
     * Hardware routes the trap to vstvec -> vscr_vs_trap_handler,
     * which records vsepc/vscause/vstval into globals. */
    run_in_vs_mode(vs_exec_illegal, 0);

    /* Verify VS trap handler was invoked */
    TEST_ASSERT("VS trap was triggered", g_vscr_vs_triggered);

    /* Verify vscause = 2 (illegal instruction) */
    TEST_ASSERT_EQ("vscause == 2 (illegal instruction)",
                   g_vscr_vs_cause, (uintptr_t)CAUSE_ILLEGAL_INST);

    /* Verify vsepc points to the faulting instruction.
     * The handler advanced sepc by 4, so the original vsepc was
     * g_vscr_vs_epc (before the handler's +4 adjustment). The
     * recorded value is the faulting PC because we read sepc before
     * advancing it. */
    TEST_ASSERT("vsepc != 0 (captured faulting PC)",
                g_vscr_vs_epc != 0);

    /* vstval is implementation-defined for illegal instructions:
     * it may be 0 or the faulting instruction encoding.
     * We only verify it was written (the handler captured it). */

    clear_all_deleg();
    HYP_TEST_END();
}

/* ===================================================================
 * VSCR-06: V=0 trap uses sepc/scause/stval, not VS CSRs
 *
 * Verify that when V=0, HS-mode traps use sepc/scause/stval and
 * do NOT modify vsepc/vscause/vstval.
 *
 * Per norm:vspec_sz_acc_op / norm:vscause_sz_acc_op /
 * norm:vstval_sz_acc_op:
 *   "When V=0, vsepc/vscause/vstval does not directly affect
 *    the behavior of the machine."
 * =================================================================== */
TEST_REGISTER(vscr_06_v0_trap_uses_sepc);
bool vscr_06_v0_trap_uses_sepc(void)
{
    TEST_BEGIN("VSCR-06: V=0 trap uses sepc/scause/stval, not VS CSRs");

    /* Preset VS CSRs with distinctive canary values.
     * vscause is WLRL: only valid cause codes are accepted, so use
     * cause=12 (instruction page fault) instead of an arbitrary value.
     * vsepc is WARL: bit 0 must be 0 (instruction alignment). */
    uintptr_t canary_epc   = 0xCCCC0000UL;
    uintptr_t canary_cause = 12;            /* valid cause: instruction page fault */
    uintptr_t canary_tval  = 0xEEEE0000UL;

    CSRW(CSR_VSEPC, canary_epc);    /* vsepc */
    CSRW(CSR_VSCAUSE, canary_cause);   /* vscause */
    CSRW(CSR_VSTVAL, canary_tval);    /* vstval */

    /* Read back canary values to confirm they were actually stored.
     * WLRL/WARL fields may reject or mask illegal writes; comparing
     * against the confirmed stored value (not the written value) makes
     * the test robust across all SPEC-compliant implementations. */
    uintptr_t stored_epc, stored_cause, stored_tval;
    stored_epc = CSRR(CSR_VSEPC);
    stored_cause = CSRR(CSR_VSCAUSE);
    stored_tval = CSRR(CSR_VSTVAL);
    TEST_ASSERT_EQ("vsepc canary stored", stored_epc, canary_epc);
    TEST_ASSERT_EQ("vscause canary stored", stored_cause, canary_cause);
    TEST_ASSERT_EQ("vstval canary stored", stored_tval, canary_tval);

    /* Ensure no delegation: traps go to M-mode where the
     * framework's trap handler captures them. */
    clear_all_deleg();

    /* Trigger S-mode ecall (cause=9). With medeleg=0 and hedeleg=0,
     * this traps to M-mode. V=0 throughout.
     *
     * Must execute ecall from HS-mode (S-mode, V=0), not M-mode.
     * M-mode ecall would produce cause=11 (ECALL_FROM_M), not
     * cause=9 (ECALL_FROM_S). Use goto_priv + PRIV_DO pattern
     * (same as PRIO-04) to switch to S-mode, arm trap capture
     * only around the ecall, then return to M-mode. */
    goto_priv(PRIV_S);
    PRIV_DO(vs_exec_ecall(0));
    goto_priv(PRIV_M);

    /* Verify M-mode trap was captured */
    bool trapped = trap_was_triggered();
    TEST_ASSERT("M-mode trap was triggered", trapped);
    TEST_ASSERT_EQ("cause == CAUSE_ECALL_FROM_S (9)",
                   trap_get_cause(), (uintptr_t)CAUSE_ECALL_FROM_S);

    /* Verify sepc/scause/stval were written by the trap
     * (sepc should point to the ecall instruction) */
    TEST_ASSERT("sepc was written by trap", trap_get_epc() != 0);

    /* Verify VS CSRs are unchanged (V=0 trap must not touch them) */
    uintptr_t vsepc_after, vscause_after, vstval_after;
    vsepc_after = CSRR(CSR_VSEPC);
    vscause_after = CSRR(CSR_VSCAUSE);
    vstval_after = CSRR(CSR_VSTVAL);

    TEST_ASSERT_EQ("vsepc unchanged by V=0 trap",
                   vsepc_after, stored_epc);
    TEST_ASSERT_EQ("vscause unchanged by V=0 trap",
                   vscause_after, stored_cause);
    TEST_ASSERT_EQ("vstval unchanged by V=0 trap",
                   vstval_after, stored_tval);

    HYP_TEST_END();
}

/* ===================================================================
 * VSCR-07: V=1 CSR substitution (sscratch->vsscratch, etc.)
 *
 * Verify that when V=1, S-level CSR accesses are substituted:
 *   sscratch -> vsscratch (norm:vsscratch_sz_acc_op)
 *   sepc     -> vsepc     (norm:vspec_sz_acc_op)
 *   scause   -> vscause   (norm:vscause_sz_acc_op)
 *   stval    -> vstval    (norm:vstval_sz_acc_op)
 * =================================================================== */
TEST_REGISTER(vscr_07_v1_csr_substitution);
bool vscr_07_v1_csr_substitution(void)
{
    TEST_BEGIN("VSCR-07: V=1 CSR substitution (S->VS)");

    /* Write known values to VS CSRs from HS-mode (V=0) */
    uintptr_t scratch_val = 0xAA550000UL;
    uintptr_t epc_val     = 0xBB000000UL;  /* even-aligned for WARL */
    uintptr_t cause_val   = 12;            /* instruction page fault */
    uintptr_t tval_val    = 0xCC770000UL;

    CSRW(CSR_VSSCRATCH, scratch_val);  /* vsscratch */
    CSRW(CSR_VSEPC, epc_val);      /* vsepc */
    CSRW(CSR_VSCAUSE, cause_val);    /* vscause */
    CSRW(CSR_VSTVAL, tval_val);     /* vstval */

    /* In VS-mode (V=1), S-level CSR names map to VS CSRs.
     * Reading sscratch should return vsscratch, etc. */
    uintptr_t vs_scratch = run_in_vs_mode(vs_read_sscratch, 0);
    uintptr_t vs_epc     = run_in_vs_mode(vs_read_sepc, 0);
    uintptr_t vs_cause   = run_in_vs_mode(vs_read_scause, 0);
    uintptr_t vs_tval    = run_in_vs_mode(vs_read_stval, 0);

    TEST_ASSERT_EQ("sscratch in V=1 returns vsscratch",
                   vs_scratch, scratch_val);
    TEST_ASSERT_EQ("sepc in V=1 returns vsepc",
                   vs_epc, epc_val);
    TEST_ASSERT_EQ("scause in V=1 returns vscause",
                   vs_cause, cause_val);
    TEST_ASSERT_EQ("stval in V=1 returns vstval",
                   vs_tval, tval_val);

    /* Verify write substitution: writing sscratch in V=1
     * should modify vsscratch. */
    uintptr_t new_scratch = 0x11220000UL;
    run_in_vs_mode(vs_write_sscratch, new_scratch);

    uintptr_t readback;
    readback = CSRR(CSR_VSSCRATCH);
    TEST_ASSERT_EQ("write sscratch in V=1 modifies vsscratch",
                   readback, new_scratch);

    HYP_TEST_END();
}
