/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * test_vstimecmp.c - VSTC: vstimecmp timer tests
 *
 * Group 7 of Hypervisor CSR subset test plan.
 * =================================================================== */

#include "hyp_test_helpers.h"

/* Delay loop: spin to allow hardware to propagate vstimecmp → VSTIP */
#define VSTC_DELAY() do { for (volatile int _i = 0; _i < 100; _i++) {} } while(0)

/* ===================================================================
 * VSTC-01: vstimecmp basic read/write
 *
 * Verify vstimecmp can be written and read back correctly.
 * =================================================================== */
TEST_REGISTER(vstc_01_basic_rw);
bool vstc_01_basic_rw(void)
{
    TEST_BEGIN("VSTC-01: vstimecmp basic read/write");

    uintptr_t test_val = 0xDEADBEEF;

    /* Write vstimecmp */
    CSRW(CSR_VSTIMECMP, test_val);

    /* Read back and verify */
    uintptr_t val;
    val = CSRR(CSR_VSTIMECMP);

    TEST_ASSERT_EQ("vstimecmp readback matches written value", val, test_val);

    HYP_TEST_END();
}

/* ===================================================================
 * VSTC-02: vstimecmp triggers VSTIP
 *
 * Verify that setting vstimecmp to 0 (or past) triggers VSTIP
 * when STCE is enabled in both henvcfg and menvcfg.
 * =================================================================== */
TEST_REGISTER(vstc_02_triggers_vstip);
bool vstc_02_triggers_vstip(void)
{
    TEST_BEGIN("VSTC-02: vstimecmp triggers VSTIP");

    /* Enable STCE: menvcfg first (M-level gates HS-level per spec).
     * menvcfg is M-level config; set STCE via the adaptive wrapper. */
    tsbi_csr_set(CSR_MENVCFG, 1UL << 63);  /* STCE bit */
    henvcfg_set_stce(true);

    /* Clear hvip.VSTIP to isolate vstimecmp-driven signal */
    uintptr_t vstip_bit = (1UL << 6);
    CSRC(CSR_HVIP, vstip_bit);

    /* Ensure clean initial state: vstimecmp = MAX */
    CSRW(CSR_VSTIMECMP, (uintptr_t)-1);
    VSTC_DELAY();

    /* Set vstimecmp to 0 to trigger interrupt */
    CSRW(CSR_VSTIMECMP, 0);
    VSTC_DELAY();

    /* Check hip.VSTIP is set (bit 6) */
    uintptr_t hip;
    hip = CSRR(CSR_HIP);  /* hip, not vsip */
    TEST_ASSERT("hip.VSTIP is set", hip & (1UL << 6));

    /* Cleanup: disarm timer, then disable STCE (HS before M) */
    CSRW(CSR_VSTIMECMP, (uintptr_t)-1);
    henvcfg_set_stce(false);
    tsbi_csr_clear(CSR_MENVCFG, 1UL << 63);

    HYP_TEST_END();
}

/* ===================================================================
 * VSTC-03: vstimecmp clears VSTIP
 *
 * Verify that writing a large value to vstimecmp clears VSTIP.
 * =================================================================== */
TEST_REGISTER(vstc_03_clears_vstip);
bool vstc_03_clears_vstip(void)
{
    TEST_BEGIN("VSTC-03: vstimecmp clears VSTIP");

    /* Enable STCE: menvcfg first (M-level gates HS-level per spec).
     * menvcfg is M-level config; set STCE via the adaptive wrapper. */
    tsbi_csr_set(CSR_MENVCFG, 1UL << 63);
    henvcfg_set_stce(true);

    /* Clear hvip.VSTIP to isolate vstimecmp-driven signal */
    uintptr_t vstip_bit = (1UL << 6);
    CSRC(CSR_HVIP, vstip_bit);

    /* Ensure clean initial state: vstimecmp = MAX (not expired) */
    CSRW(CSR_VSTIMECMP, (uintptr_t)-1);
    VSTC_DELAY();

    /* Set vstimecmp to 0 to trigger VSTIP, wait for propagation */
    CSRW(CSR_VSTIMECMP, 0);
    VSTC_DELAY();

    /* Verify VSTIP is set */
    uintptr_t hip;
    hip = CSRR(CSR_HIP);  /* hip, not vsip */
    TEST_ASSERT("hip.VSTIP initially set", hip & (1UL << 6));

    /* Write large value to clear VSTIP, wait for propagation */
    CSRW(CSR_VSTIMECMP, (uintptr_t)-1);
    VSTC_DELAY();

    /* Check hip.VSTIP is cleared */
    hip = CSRR(CSR_HIP);  /* hip, not vsip */
    TEST_ASSERT("hip.VSTIP cleared", !(hip & (1UL << 6)));

    /* Cleanup (HS before M) */
    henvcfg_set_stce(false);
    tsbi_csr_clear(CSR_MENVCFG, 1UL << 63);

    HYP_TEST_END();
}

/* ===================================================================
 * VSTC-04: VS accesses vstimecmp via stimecmp
 *
 * Verify that VS-mode writing to stimecmp actually writes to vstimecmp.
 * Per spec, when V=1, stimecmp (CSR 0x14D) is an alias for vstimecmp
 * (CSR 0x24D).
 * =================================================================== */

/* VS-mode trampoline: write stimecmp (which maps to vstimecmp). */
static uintptr_t vs_write_stimecmp(uintptr_t val)
{
    CSRW(CSR_STIMECMP, val);
    return 0;
}

TEST_REGISTER(vstc_04_vs_access_via_stimecmp);
bool vstc_04_vs_access_via_stimecmp(void)
{
    TEST_BEGIN("VSTC-04: VS accesses vstimecmp via stimecmp");

    /* Enable STCE so VS-mode can access stimecmp (=vstimecmp).
     * Per spec, VS-mode access to stimecmp requires ALL of:
     *   1. menvcfg.STCE = 1
     *   2. henvcfg.STCE = 1
     *   3. mcounteren.TM = 1
     *   4. hcounteren.TM = 1 */
    uintptr_t saved_menvcfg = tsbi_csr_read(CSR_MENVCFG);
    uintptr_t saved_mctr = tsbi_csr_read(CSR_MCOUNTEREN);
    uintptr_t saved_hctr = hcounteren_read();
    tsbi_csr_write(CSR_MENVCFG, saved_menvcfg | MENVCFG_STCE);
    henvcfg_set_stce(true);
    tsbi_csr_set(CSR_MCOUNTEREN, MCOUNTEREN_TM);
    hcounteren_set(HCOUNTEREN_TM);

    uintptr_t test_val = 0x12345678;

    /* Disarm timer first */
    CSRW(CSR_VSTIMECMP, (uintptr_t)-1);

    /* VS-mode writes stimecmp (should map to vstimecmp) */
    run_in_vs_mode(vs_write_stimecmp, test_val);

    /* Read vstimecmp from M-mode (CSR 0x24D) and verify */
    uintptr_t val;
    val = CSRR(CSR_VSTIMECMP);

    TEST_ASSERT_EQ("vstimecmp == value written by VS stimecmp",
                   val, test_val);

    /* Cleanup */
    CSRW(CSR_VSTIMECMP, (uintptr_t)-1);
    henvcfg_set_stce(false);
    tsbi_csr_write(CSR_MENVCFG, saved_menvcfg);
    tsbi_csr_write(CSR_MCOUNTEREN, saved_mctr);
    hcounteren_write(saved_hctr);

    HYP_TEST_END();
}

/* ===================================================================
 * VS-mode interrupt handler for VSTC-05
 *
 * Captures the first interrupt cause, clears the timer by writing
 * vstimecmp=MAX, disables SIE/SPIE to prevent re-entry, and returns.
 * =================================================================== */
static volatile uintptr_t g_vstc_vs_int_cause;
static volatile bool      g_vstc_vs_int_triggered;

static void vstc_vs_int_handler(void) __attribute__((naked, aligned(4)));
static void vstc_vs_int_handler(void)
{
    asm volatile (
        "addi   sp, sp, -32\n\t"
        "sd     ra, 0(sp)\n\t"
        "sd     t0, 8(sp)\n\t"
        "sd     t1, 16(sp)\n\t"
        "sd     t2, 24(sp)\n\t"

        /* Record cause only on first entry */
        "la     t2, g_vstc_vs_int_triggered\n\t"
        "lb     t0, 0(t2)\n\t"
        "bnez   t0, 1f\n\t"

        "csrr   t0, scause\n\t"
        "la     t2, g_vstc_vs_int_cause\n\t"
        "sd     t0, 0(t2)\n\t"
        "li     t0, 1\n\t"
        "la     t2, g_vstc_vs_int_triggered\n\t"
        "sb     t0, 0(t2)\n\t"

        "1:\n\t"
        /* Clear VSTIP: write vstimecmp (via stimecmp alias) to MAX */
        "li     t0, -1\n\t"
        "csrw " CSR_STR(CSR_STIMECMP) ", t0\n\t"

        /* Disable SIE (bit 1) and SPIE (bit 5) to prevent re-entry */
        "li     t0, 0x22\n\t"
        "csrc   sstatus, t0\n\t"

        /* Force SPP=1 so sret returns to VS-mode */
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

/* VS-mode trampoline: trigger timer interrupt by writing stimecmp=0 */
static uintptr_t vs_trigger_vstimecmp(uintptr_t arg)
{
    (void)arg;
    /* Write stimecmp (=vstimecmp) to 0 to trigger VSTIP */
    CSRW(CSR_STIMECMP, 0);
    /* Spin to allow interrupt delivery */
    for (volatile int i = 0; i < 1000; i++) {}
    return 0;
}

/* ===================================================================
 * VSTC-05: vstimecmp interrupt delegation to VS
 *
 * Verify that timer interrupts can be delegated to VS-mode.
 * Configures full delegation chain M->HS->VS, enables hie.VSTIE
 * and vsie.STIE, triggers vstimecmp, and verifies VS-mode receives
 * cause=5 (S-level timer interrupt, translated from VSTIP).
 * =================================================================== */
TEST_REGISTER(vstc_05_interrupt_delegation_to_vs);
bool vstc_05_interrupt_delegation_to_vs(void)
{
    TEST_BEGIN("VSTC-05: vstimecmp interrupt delegation to VS");

    /* Enable STCE for vstimecmp comparison logic.
     * VS-mode access to stimecmp (in handler + trampoline) requires
     * mcounteren.TM and hcounteren.TM in addition to STCE. */
    uintptr_t saved_menvcfg = tsbi_csr_read(CSR_MENVCFG);
    uintptr_t saved_mctr = tsbi_csr_read(CSR_MCOUNTEREN);
    uintptr_t saved_hctr = hcounteren_read();
    tsbi_csr_write(CSR_MENVCFG, saved_menvcfg | MENVCFG_STCE);
    henvcfg_set_stce(true);
    tsbi_csr_set(CSR_MCOUNTEREN, MCOUNTEREN_TM);
    hcounteren_set(HCOUNTEREN_TM);

    /* Clear state */
    g_vstc_vs_int_cause = 0;
    g_vstc_vs_int_triggered = false;

    /* Clear interrupt sources */
    CSRW(CSR_HIE, 0);   /* hie = 0 */
    CSRW(CSR_HVIP, 0);   /* hvip = 0 */
    CSRW(CSR_VSTIMECMP, (uintptr_t)-1);

    /* Delegate M->HS: mideleg[5] (STIP) */
    tsbi_csr_set(CSR_MIDELEG, 1UL << 5);

    /* Delegate HS->VS: hideleg[6] (VSTIP) */
    uintptr_t saved_hideleg = hideleg_read();
    hideleg_write(saved_hideleg | (1UL << 6));

    /* Enable hie.VSTIE (bit 6) */
    CSRS(CSR_HIE, 1UL << 6);

    /* Enable vsie.STIE (bit 5) */
    CSRW(CSR_VSIE, 1UL << 5);

    /* Install VS-mode trap handler (Direct mode) */
    vs_trap_setup_direct((uintptr_t)vstc_vs_int_handler);

    /* Enable vsstatus.SIE (bit 1) */
    CSRS(CSR_VSSTATUS, MSTATUS_SIE_BIT);

    /* (removed) "Set mstatus.MPIE=1 so MIE=1 after mret" is obsolete under
     * S-mode-normal: MPIE is a return-path bit the tsbi_csr_ guard refuses to proxy
     * and every framework excursion re-enters via mret (MPIE<-1). The VS timer
     * interrupt is delivered per vsstatus.SIE (enabled above) + hideleg[6] +
     * vsie.STIE + hie.VSTIE, not by mstatus.MIE (which only gates interrupts
     * while executing in M-mode). */

    /* Disarm timer */
    CSRW(CSR_VSTIMECMP, (uintptr_t)-1);

    /* Enter VS-mode: write vstimecmp=0 to trigger timer */
    run_in_vs_mode(vs_trigger_vstimecmp, 0);

    /* Verify VS-mode received the timer interrupt with cause=5 */
    TEST_ASSERT("VS-mode interrupt was triggered",
                g_vstc_vs_int_triggered);
    uintptr_t expected_cause = CAUSE_INTERRUPT_BIT | CAUSE_S_TIMER_INTERRUPT;
    TEST_ASSERT_EQ("vscause == interrupt | 5 (timer)",
                   g_vstc_vs_int_cause, expected_cause);

    /* Cleanup */
    CSRW(CSR_VSTIMECMP, (uintptr_t)-1);
    CSRW(CSR_HIE, 0);
    CSRW(CSR_VSIE, 0);
    henvcfg_set_stce(false);
    tsbi_csr_write(CSR_MENVCFG, saved_menvcfg);
    tsbi_csr_write(CSR_MCOUNTEREN, saved_mctr);
    hcounteren_write(saved_hctr);
    hideleg_write(saved_hideleg);
    /* Restore mideleg */
    tsbi_csr_clear(CSR_MIDELEG, 1UL << 5);

    HYP_TEST_END();
}

/* ===================================================================
 * VSTC-06: vstimecmp interrupt traps to HS
 *
 * Verify that timer interrupts are visible at HS-mode when hideleg[6]=0
 * (not delegated to VS). M->HS delegation via mideleg is enabled so the
 * interrupt is pending at HS level, but not forwarded to VS-mode.
 * =================================================================== */
TEST_REGISTER(vstc_06_interrupt_trap_to_hs);
bool vstc_06_interrupt_trap_to_hs(void)
{
    TEST_BEGIN("VSTC-06: vstimecmp interrupt traps to HS");

    /* Enable STCE for vstimecmp comparison logic */
    uintptr_t saved_menvcfg = tsbi_csr_read(CSR_MENVCFG);
    tsbi_csr_write(CSR_MENVCFG, saved_menvcfg | MENVCFG_STCE);
    henvcfg_set_stce(true);

    /* Clear hvip and vstimecmp */
    CSRW(CSR_HVIP, 0);
    CSRW(CSR_VSTIMECMP, (uintptr_t)-1);
    VSTC_DELAY();

    /* Delegate M->HS: mideleg[5] (STIP) */
    tsbi_csr_set(CSR_MIDELEG, 1UL << 5);

    /* Do NOT delegate to VS: clear hideleg[6] (VSTIP) */
    uintptr_t saved_hideleg = hideleg_read();
    hideleg_write(saved_hideleg & ~(1UL << 6));

    /* Trigger VSTIP: write vstimecmp=0 */
    CSRW(CSR_VSTIMECMP, 0);
    VSTC_DELAY();

    /* Verify hip.VSTIP is set (visible at HS level) */
    uintptr_t hip;
    hip = CSRR(CSR_HIP);
    TEST_ASSERT("hip.VSTIP set (HS-level pending)",
                hip & (1UL << 6));

    /* Enter VS-mode and verify interrupt NOT delivered to VS.
     * With hideleg[6]=0, vsip.STIP must remain 0. */
    g_vstc_vs_int_cause = 0;
    g_vstc_vs_int_triggered = false;
    run_in_vs_mode(vs_nop_fn, 0);
    TEST_ASSERT("VS-mode interrupt NOT triggered (hideleg[6]=0)",
                !g_vstc_vs_int_triggered);

    /* Cleanup */
    CSRW(CSR_VSTIMECMP, (uintptr_t)-1);
    VSTC_DELAY();
    henvcfg_set_stce(false);
    tsbi_csr_write(CSR_MENVCFG, saved_menvcfg);
    hideleg_write(saved_hideleg);
    tsbi_csr_clear(CSR_MIDELEG, 1UL << 5);

    HYP_TEST_END();
}

/* ===================================================================
 * VSTC-07: htimedelta affects vstimecmp comparison
 *
 * Verify that htimedelta offset affects the effective timer comparison.
 * Per spec, VSTIP is set when (time + htimedelta) >= vstimecmp.
 * We set htimedelta to a large offset, then set vstimecmp to a value
 * that is in the past relative to (time + htimedelta) but potentially
 * in the future relative to raw time, proving the offset is applied.
 *
 * NOTE: htimedelta (CSR 0x605) is read-write from HS-mode.
 * =================================================================== */
TEST_REGISTER(vstc_07_htimedelta_affects_comparison);
bool vstc_07_htimedelta_affects_comparison(void)
{
    TEST_BEGIN("VSTC-07: htimedelta affects vstimecmp comparison");

    /* Enable STCE for vstimecmp comparison logic */
    uintptr_t saved_menvcfg = tsbi_csr_read(CSR_MENVCFG);
    tsbi_csr_write(CSR_MENVCFG, saved_menvcfg | MENVCFG_STCE);
    henvcfg_set_stce(true);

    /* Clear hvip and disarm vstimecmp */
    CSRW(CSR_HVIP, 0);
    CSRW(CSR_VSTIMECMP, (uintptr_t)-1);
    VSTC_DELAY();

    /* Save and set htimedelta to a large offset */
    uintptr_t saved_htd;
    saved_htd = CSRR(CSR_HTIMEDELTA);
    uintptr_t delta = 0x10000000UL;
    htimedelta_write(delta);

    /* Read current time (raw, from M-mode perspective) */
    uintptr_t now;
    now = CSRR(CSR_TIME);

    /* Set vstimecmp = now + delta/2.
     * Since (time + htimedelta) = time + delta, and
     * vstimecmp = now + delta/2 (where now ~ time),
     * we have (time + delta) > (now + delta/2) for small time drift,
     * so VSTIP should trigger. */
    CSRW(CSR_VSTIMECMP, now + (delta >> 1));
    VSTC_DELAY();

    /* Check hip.VSTIP */
    uintptr_t hip;
    hip = CSRR(CSR_HIP);
    TEST_ASSERT("VSTIP triggered with htimedelta offset",
                hip & (1UL << 6));

    /* Cleanup */
    CSRW(CSR_VSTIMECMP, (uintptr_t)-1);
    VSTC_DELAY();
    henvcfg_set_stce(false);
    tsbi_csr_write(CSR_MENVCFG, saved_menvcfg);
    htimedelta_write(saved_htd);

    HYP_TEST_END();
}
