/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * Test Group 8: hedeleg exception delegation chain
 *
 * Tests DELEG-04~07 and DELEG-15/16 verify exception delegation to
 * VS-mode and non-delegatable exception constraints.
 * Split from Hypervisor/tests/test_delegation.c.
 * See DOCS/testplan/Hypervisor_Exceptions_test_plan.md.
 */

#include "hyp_test_helpers.h"
/* ===================================================================
 * VS-mode exception handler for delegation tests.
 *
 * Records vscause, advances sepc by 4 bytes (to skip the faulting
 * instruction: ecall/ebreak/UNIMP are all 4-byte instructions),
 * clears sstatus.SIE+SPIE, forces SPP=1 (VS-mode), then returns
 * via sret.
 *
 * NOTE: SPP must be explicitly set to 1 before sret. When the trap
 * originates from VU-mode, hardware sets vsstatus.SPP=0 (U-level),
 * which would cause sret to return to VU-mode instead of VS-mode.
 * The _v_trampoline expects to run in VS-mode so its final ecall
 * generates cause=10 (ecall-from-VS) for the M-mode return path.
 * =================================================================== */

static volatile uintptr_t g_vs_exc_cause;
static volatile bool g_vs_exc_triggered;

static void vs_exc_handler(void) __attribute__((naked, aligned(4)));
static void vs_exc_handler(void)
{
    asm volatile (
        "addi   sp, sp, -32\n\t"
        "sd     ra, 0(sp)\n\t"
        "sd     t0, 8(sp)\n\t"
        "sd     t1, 16(sp)\n\t"
        "sd     t2, 24(sp)\n\t"

        /* Record vscause */
        "csrr   t0, scause\n\t"
        "la     t2, g_vs_exc_cause\n\t"
        "sd     t0, 0(t2)\n\t"
        "li     t0, 1\n\t"
        "la     t2, g_vs_exc_triggered\n\t"
        "sb     t0, 0(t2)\n\t"

        /* Advance sepc by 4 to skip the faulting instruction */
        "csrr   t0, sepc\n\t"
        "addi   t0, t0, 4\n\t"
        "csrw   sepc, t0\n\t"

        /* Clear SIE (bit 1) and SPIE (bit 5) to prevent re-entry */
        "li     t0, 0x22\n\t"
        "csrc   sstatus, t0\n\t"

        /* Force SPP=1 (S-mode) so sret returns to VS-mode, not VU.
         * When the trap came from VU-mode, hardware set SPP=0. */
        "li     t0, 0x100\n\t"
        "csrs   sstatus, t0\n\t"

        /* Restore registers */
        "ld     ra, 0(sp)\n\t"
        "ld     t0, 8(sp)\n\t"
        "ld     t1, 16(sp)\n\t"
        "ld     t2, 24(sp)\n\t"
        "addi   sp, sp, 32\n\t"

        "sret\n\t"
    );
}

/* ===================================================================
 * Helper: set up VS exception test infrastructure.
 *
 * Configures medeleg/hedeleg for the given exception mask and installs
 * the VS exception handler at vstvec.
 * =================================================================== */
static void setup_vs_exc_test(uintptr_t exc_mask)
{
    g_vs_exc_cause = 0;
    g_vs_exc_triggered = false;

    /* Configure dual-layer delegation: M->HS (medeleg) -> VS (hedeleg) */
    setup_deleg_to_vs(exc_mask, 0);

    /* Install VS-mode trap handler (Direct mode) */
    vs_trap_setup_direct((uintptr_t)vs_exc_handler);

    /* (removed) The old "set mstatus.MPIE=1 so MIE=1 after mret into VS-mode"
     * is obsolete under S-mode-normal: mstatus is M-level (the raw csrr traps
     * from S), MPIE is a return-path bit the tsbi_csr_ guard refuses to proxy, and
     * every framework excursion re-enters VS via mret (MPIE<-1) anyway. It is
     * also unnecessary -- these tests route an EXCEPTION into VS via
     * hedeleg+vstvec; exception delivery does not depend on mstatus.MIE (which
     * only gates interrupts while executing in M-mode). */
}

/* ------------------------------------------------------------------
 * DELEG-04: hedeleg delegates illegal-instruction to VS-mode
 * ------------------------------------------------------------------ */
TEST_REGISTER(hedeleg_illegal_inst_deleg);
bool hedeleg_illegal_inst_deleg(void)
{
    TEST_BEGIN("DELEG-04: Delegate illegal-instruction to VS (vscause=2)");

    setup_vs_exc_test(1UL << 2);

    /* Trigger illegal instruction in VS-mode; hardware routes to vstvec */
    run_in_vs_mode(vs_exec_illegal, 0);

    TEST_ASSERT("VS trap was triggered", g_vs_exc_triggered);
    TEST_ASSERT_EQ("vscause == 2 (illegal instruction)",
                   g_vs_exc_cause, (uintptr_t)2);

    clear_all_deleg();
    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * DELEG-05: hedeleg NOT delegated -> trap stays at HS/M-mode
 * ------------------------------------------------------------------ */
TEST_REGISTER(hedeleg_default_trap_to_hs);
bool hedeleg_default_trap_to_hs(void)
{
    TEST_BEGIN("DELEG-05: hedeleg[10]=0, ecall traps to M/HS (not VS)");

    /* Clear hedeleg so ecall from VS is NOT delegated to VS-mode.
     * Framework default: medeleg has all bits set, so with hedeleg[10]=0
     * the ecall traps to M-mode (medeleg routes to HS, then hedeleg=0
     * means it stays at M-level). */
    hedeleg_write(0x0);

    /* (removed) The old "clear mstatus.MIE to prevent spurious interrupts" is
     * obsolete under S-mode-normal: mstatus is M-level (the raw csrr traps from
     * S) and MIE is a return-path bit the tsbi_csr_ guard refuses to proxy. It is
     * also unnecessary -- mstatus.MIE only gates interrupts while executing in
     * M-mode, and the framework controls the interrupt state across the
     * run_in_vs_mode excursion. */

    trap_expect_begin();
    run_in_vs_mode(vs_exec_ecall, 0);

    TEST_ASSERT("trap was triggered at M/HS level", trap_was_triggered());
    TEST_ASSERT_EQ("cause == 10 (ecall from VS-mode, not delegated to VS)",
                   trap_get_cause(), (uintptr_t)10);
    trap_expect_end();

    clear_all_deleg();
    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * DELEG-06: hedeleg delegates breakpoint to VS-mode
 * ------------------------------------------------------------------ */
TEST_REGISTER(hedeleg_breakpoint_deleg);
bool hedeleg_breakpoint_deleg(void)
{
    TEST_BEGIN("DELEG-06: Delegate breakpoint to VS (vscause=3)");

#ifdef SKIP_BREAKPOINT_TESTS
    TEST_SKIP("platform does not support breakpoint (SKIP_BREAKPOINT_TESTS)");
#endif

    setup_vs_exc_test(1UL << 3);

    run_in_vs_mode(vs_exec_ebreak, 0);

    TEST_ASSERT("VS trap was triggered", g_vs_exc_triggered);
    TEST_ASSERT_EQ("vscause == 3 (breakpoint)",
                   g_vs_exc_cause, (uintptr_t)3);

    clear_all_deleg();
    HYP_TEST_END();
}

/* DELEG-07 stimulus: a plain guest ecall, hardware-delegated to VS and
 * recorded by vs_exc_handler. Deliberately does NOT call tsbi_arm_raw_ecall()
 * the way the shared vs_exec_ecall does: that arms a consume-once escape flag
 * cleared only by the M/HS handler's P1 stage, but here the ecall is delegated
 * straight to the custom VS handler, which never clears it. The stale flag
 * would then make the M handler treat run_in_vu_mode's own return ecall (the
 * T-SBI GOTO) as a raw stimulus and skip its dispatch -- a fatal unexpected
 * trap. The custom VS handler records vscause directly, so no escape arming is
 * needed here. */
static uintptr_t deleg_guest_ecall(uintptr_t arg)
{
    (void)arg;
    /* Force a0 to the explicit invalid-opcode sentinel (rather than relying
     * on an incidental a0 value) before issuing the stimulus ecall. */
    asm volatile ("li a0, %0\n\t"
                  "ecall"
                  :: "i"((uintptr_t)0xFFUL) : "a0", "memory");
    return 0;
}

/* ------------------------------------------------------------------
 * DELEG-07: hedeleg delegates ecall-from-VU to VS-mode
 * ------------------------------------------------------------------ */
TEST_REGISTER(hedeleg_ecall_vu_deleg);
bool hedeleg_ecall_vu_deleg(void)
{
    TEST_BEGIN("DELEG-07: Delegate ecall-from-VU to VS (vscause=8)");

    setup_vs_exc_test(1UL << 8);

    /* Enter VU with the one-way goto_priv() instead of run_in_vu_mode().
     * run_in_vu_mode() clears hedeleg[8] before mret so that its VU
     * trampoline's return ecall reaches M -- which would erase the
     * hedeleg[8]=1 delegation configured above. goto_priv(PRIV_VU) switches
     * privilege via an ecall-from-S (cause 9 -> M) and never touches
     * hedeleg, so the delegation stays in effect and the stimulus ecall
     * below is delegated to VS. The custom VS handler records vscause and
     * forces vsstatus.SPP=1 so its sret resumes execution in VS-mode; the
     * follow-up goto_priv(PRIV_S) then returns to HS. */
    goto_priv(PRIV_VU);
    deleg_guest_ecall(0);
    goto_priv(PRIV_S);

    TEST_ASSERT("VS trap was triggered", g_vs_exc_triggered);
    TEST_ASSERT_EQ("vscause == 8 (ecall from VU-mode)",
                   g_vs_exc_cause, (uintptr_t)8);

    clear_all_deleg();
    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * DELEG-15: guest-page-fault bits (20/21/23) are not delegatable
 * ------------------------------------------------------------------ */
TEST_REGISTER(guest_page_fault_not_delegatable);
bool guest_page_fault_not_delegatable(void)
{
    TEST_BEGIN("DELEG-15: Verify guest-page-fault bits (20/21/23) are read-zero");

    hedeleg_write(0xFFFFFFFF);
    uintptr_t val = hedeleg_read();

    uintptr_t gpf_bits = (1UL << 20) | (1UL << 21) | (1UL << 23);
    TEST_ASSERT_EQ("hedeleg bits 20/21/23 (guest-page-fault) must be read-zero",
                   val & gpf_bits, (uintptr_t)0);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * DELEG-16: virtual-instruction bit (22) is not delegatable
 * ------------------------------------------------------------------ */
TEST_REGISTER(virtual_inst_not_delegatable);
bool virtual_inst_not_delegatable(void)
{
    TEST_BEGIN("DELEG-16: Verify virtual-instruction bit (22) is read-zero");

    hedeleg_write(0xFFFFFFFF);
    uintptr_t val = hedeleg_read();

    TEST_ASSERT_EQ("hedeleg bit 22 (virtual-instruction) must be read-zero",
                   val & (1UL << 22), (uintptr_t)0);

    HYP_TEST_END();
}
