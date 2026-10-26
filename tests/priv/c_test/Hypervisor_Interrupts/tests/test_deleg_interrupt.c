/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * Test Group 4: hideleg interrupt delegation and cause translation
 *
 * Tests DELEG-08 through DELEG-14 verify interrupt delegation to
 * VS-mode and VS interrupt number translation.
 * Split from Hypervisor/tests/test_delegation.c.
 * See DOCS/testplan/Hypervisor_Interrupts_test_plan.md.
 */

#include "hyp_test_helpers.h"
/* ===================================================================
 * VS-level interrupt cause codes (translated from VS to S level).
 *   VSSI (hvip bit 2)  -> vscause = 1 (SSI)
 *   VSTI (hvip bit 6)  -> vscause = 5 (STI)
 *   VSEI (hvip bit 10) -> vscause = 9 (SEI)
 * =================================================================== */
#define VS_IRQ_SSI   (CAUSE_INTERRUPT_BIT | 1)
#define VS_IRQ_STI   (CAUSE_INTERRUPT_BIT | 5)
#define VS_IRQ_SEI   (CAUSE_INTERRUPT_BIT | 9)

/* VS_VSSIP / VS_VSTIP / VS_VSEIP are defined once in test_interrupts.c
 * (Group 1-2, included before this file in the unity build). */

/* vs_int_handler, g_vs_int_cause, g_vs_int_triggered, and
 * setup_vs_int_test() are reused from test_interrupts.c (Group 1-2,
 * same unity-build TU). The delegation tests use the same handler
 * and setup logic. */

/* ------------------------------------------------------------------
 * DELEG-08: hideleg delegates VSSI to VS-mode
 * ------------------------------------------------------------------ */
TEST_REGISTER(hideleg_vssi_deleg);
bool hideleg_vssi_deleg(void)
{
    TEST_BEGIN("DELEG-08: Delegate VSSI to VS (vscause=1, translated)");

    setup_vs_int_test(VS_VSSIP);
    CSRS(CSR_HIE, VS_VSSIP);
    hvip_set_vssi(1);

    run_in_vs_mode(vs_nop_fn, 0);

    TEST_ASSERT("VS interrupt was triggered", g_vs_int_triggered);
    TEST_ASSERT_EQ("vscause == 1 (SSI, translated from VSSI)",
                   g_vs_int_cause, (uintptr_t)VS_IRQ_SSI);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * DELEG-09: hideleg delegates VSTI to VS-mode
 * ------------------------------------------------------------------ */
TEST_REGISTER(hideleg_vsti_deleg);
bool hideleg_vsti_deleg(void)
{
    TEST_BEGIN("DELEG-09: Delegate VSTI to VS (vscause=5, translated)");

    setup_vs_int_test(VS_VSTIP);
    CSRS(CSR_HIE, VS_VSTIP);
    hvip_set_vsti(1);

    run_in_vs_mode(vs_nop_fn, 0);

    TEST_ASSERT("VS interrupt was triggered", g_vs_int_triggered);
    TEST_ASSERT_EQ("vscause == 5 (STI, translated from VSTI)",
                   g_vs_int_cause, (uintptr_t)VS_IRQ_STI);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * DELEG-10: hideleg delegates VSEI to VS-mode
 * ------------------------------------------------------------------ */
TEST_REGISTER(hideleg_vsei_deleg);
bool hideleg_vsei_deleg(void)
{
    TEST_BEGIN("DELEG-10: Delegate VSEI to VS (vscause=9, translated)");

    setup_vs_int_test(VS_VSEIP);
    CSRS(CSR_HIE, VS_VSEIP);
    hvip_set_vsei(1);

    run_in_vs_mode(vs_nop_fn, 0);

    TEST_ASSERT("VS interrupt was triggered", g_vs_int_triggered);
    TEST_ASSERT_EQ("vscause == 9 (SEI, translated from VSEI)",
                   g_vs_int_cause, (uintptr_t)VS_IRQ_SEI);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * DELEG-11: hideleg NOT delegated -> interrupt not delivered to VS
 * ------------------------------------------------------------------ */
TEST_REGISTER(hideleg_not_deleg_trap_to_hs);
bool hideleg_not_deleg_trap_to_hs(void)
{
    TEST_BEGIN("DELEG-11: hideleg[2]=0, VSSIP not delivered to VS-mode");

    hideleg_write(0);

    /* Inject VSSIP */
    hvip_set_vssi(1);

    /* Verify VSSIP is pending in hip (HS-visible) */
    uintptr_t hip_val;
    hip_val = CSRR(CSR_HIP);
    TEST_ASSERT_EQ("hip.VSSIP should be pending (HS-visible)",
                   hip_val & VS_VSSIP, VS_VSSIP);

    /* VS-mode reads sip (= vsip in V=1): SSIP must be 0 (not delegated) */
    uintptr_t sip_val = run_in_vs_mode(vs_read_sip, 0);
    TEST_ASSERT_EQ("vsip.SSIP should be 0 when hideleg[2]=0",
                   sip_val & (1UL << 1), (uintptr_t)0);

    /* Cleanup */
    hvip_set_vssi(0);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * DELEG-12: Interrupt number translation VSSI -> SSI
 * ------------------------------------------------------------------ */
TEST_REGISTER(interrupt_translation_vssi);
bool interrupt_translation_vssi(void)
{
    TEST_BEGIN("DELEG-12: VSSI->SSI translation (vscause=1, not 2)");

    setup_vs_int_test(VS_VSSIP);
    CSRS(CSR_HIE, VS_VSSIP);
    hvip_set_vssi(1);

    run_in_vs_mode(vs_nop_fn, 0);

    TEST_ASSERT("VS interrupt was triggered", g_vs_int_triggered);
    /* Key assertion: cause must be 1 (SSI), proving translation occurred */
    TEST_ASSERT_EQ("vscause == 1 (translated SSI, NOT raw VSSI=2)",
                   g_vs_int_cause, (uintptr_t)VS_IRQ_SSI);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * DELEG-13: Interrupt number translation VSTI -> STI
 * ------------------------------------------------------------------ */
TEST_REGISTER(interrupt_translation_vsti);
bool interrupt_translation_vsti(void)
{
    TEST_BEGIN("DELEG-13: VSTI->STI translation (vscause=5, not 6)");

    setup_vs_int_test(VS_VSTIP);
    CSRS(CSR_HIE, VS_VSTIP);
    hvip_set_vsti(1);

    run_in_vs_mode(vs_nop_fn, 0);

    TEST_ASSERT("VS interrupt was triggered", g_vs_int_triggered);
    TEST_ASSERT_EQ("vscause == 5 (translated STI, NOT raw VSTI=6)",
                   g_vs_int_cause, (uintptr_t)VS_IRQ_STI);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * DELEG-14: Interrupt number translation VSEI -> SEI
 * ------------------------------------------------------------------ */
TEST_REGISTER(interrupt_translation_vsei);
bool interrupt_translation_vsei(void)
{
    TEST_BEGIN("DELEG-14: VSEI->SEI translation (vscause=9, not 10)");

    setup_vs_int_test(VS_VSEIP);
    CSRS(CSR_HIE, VS_VSEIP);
    hvip_set_vsei(1);

    run_in_vs_mode(vs_nop_fn, 0);

    TEST_ASSERT("VS interrupt was triggered", g_vs_int_triggered);
    TEST_ASSERT_EQ("vscause == 9 (translated SEI, NOT raw VSEI=10)",
                   g_vs_int_cause, (uintptr_t)VS_IRQ_SEI);

    HYP_TEST_END();
}
