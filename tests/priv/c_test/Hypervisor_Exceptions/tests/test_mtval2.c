/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * Test Group 6: mtval2/mtinst registers (M-mode trap)
 *
 * Tests MTVAL-01 through MTVAL-07 verify mtval2, mtinst and htinst
 * behavior per the strict-verification principles of the test plan
 * (DOCS/testplan/Hypervisor_Exceptions_test_plan.md, Group 6):
 *  - WARL read/write tests must not demand echo of the written value;
 *    zero must be holdable and readback must be stable;
 *  - on a guest-page fault mtval2 must be exactly 0 or GPA>>2;
 *  - on an implicit VS-stage walk fault a nonzero mtval2 must be the
 *    implicit-access GPA>>2 and mtinst the read pseudoinstruction.
 *
 * In this suite traps from VS-mode are not delegated and are taken
 * into M-mode; the framework captures mtval2/mtinst at M-mode trap
 * entry, so trap_get_htval()/trap_get_htinst() reflect mtval2/mtinst.
 */

#include "hyp_test_helpers.h"

/* mtval2/mtinst are M-level trap-state CSRs: hardware rewrites them on every
 * trap into M-mode (including the T-SBI proxy ecall used by tsbi_csr_/mcsr_), so
 * they cannot be probed per-access from S(HS)-mode -- a proxy round-trip both
 * traps on the raw access and clobbers the value. Run each WARL sequence inside
 * ONE M-mode excursion (no intervening trap) and stash the reads in these
 * globals for the assertions. Any pattern works: WARL echo is not required,
 * only that zero is holdable and readback is stable. */
static uintptr_t g_warl_r0, g_warl_r1a, g_warl_r1b, g_warl_r2;

static uintptr_t mtval2_warl_probe(uintptr_t arg)
{
    (void)arg;
    uintptr_t pat = 0xDEADBEEFCAFEBABEUL;
    CSRW(CSR_MTVAL2, 0);
    g_warl_r0 = CSRR(CSR_MTVAL2);
    CSRW(CSR_MTVAL2, pat);
    g_warl_r1a = CSRR(CSR_MTVAL2);
    CSRW(CSR_MTVAL2, pat);
    g_warl_r1b = CSRR(CSR_MTVAL2);
    g_warl_r2 = CSRR(CSR_MTVAL2);
    CSRW(CSR_MTVAL2, 0);
    return 0;
}

static uintptr_t mtinst_warl_probe(uintptr_t arg)
{
    (void)arg;
    uintptr_t pat = 0x123456789ABCDEF0UL;
    CSRW(CSR_MTINST, 0);
    g_warl_r0 = CSRR(CSR_MTINST);
    CSRW(CSR_MTINST, pat);
    g_warl_r1a = CSRR(CSR_MTINST);
    CSRW(CSR_MTINST, pat);
    g_warl_r1b = CSRR(CSR_MTINST);
    g_warl_r2 = CSRR(CSR_MTINST);
    CSRW(CSR_MTINST, 0);
    return 0;
}

/* ------------------------------------------------------------------
 * MTVAL-01: mtval2 WARL read/write
 *
 * norm:mtval2_val: mtval2 is WARL; it MUST hold zero and may hold
 * only an arbitrary subset of shifted GPAs. Echoing an arbitrary
 * written value is NOT required, but the readback of any value must
 * be stable (writing the same value twice reads back identically).
 * ------------------------------------------------------------------ */
TEST_REGISTER(mtval2_basic_rw);
bool mtval2_basic_rw(void) {
    TEST_BEGIN("MTVAL-01: mtval2 WARL read/write semantics");

    /* mtval2 is M-level trap state rewritten on every M-mode trap (incl. the
     * proxy ecall), so run the whole WARL sequence in ONE M-mode excursion and
     * assert on the values captured there (see mtval2_warl_probe). */
    run_in_priv(PRIV_M, mtval2_warl_probe, 0);
    TEST_ASSERT_EQ("mtval2 must hold zero", g_warl_r0, 0);
    TEST_ASSERT_EQ("mtval2 readback must be stable", g_warl_r1a, g_warl_r1b);
    TEST_ASSERT_EQ("mtval2 value must persist", g_warl_r2, g_warl_r1a);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * MTVAL-02: mtval2 on guest-page-fault trap to M-mode
 *
 * norm:mtval2_trapval: mtval2 is written with either zero or the
 * faulting guest physical address shifted right by 2 bits. Any other
 * value is a spec violation.
 *
 * The value is observed via the framework's M-mode trap-entry capture
 * (trap_get_htval() == mtval2 on the M-mode delivery path). Reading
 * the mtval2 CSR after the VS-mode round-trip would be wrong: the
 * ecall used to leave VS-mode is itself a trap into M-mode and the
 * spec mandates mtval2 be rewritten (to zero) on every such trap.
 * ------------------------------------------------------------------ */
TEST_REGISTER(mtval2_gpf_trap);
bool mtval2_gpf_trap(void) {
    TEST_BEGIN("MTVAL-02: mtval2 on guest-page-fault trap to M-mode");

    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t victim_gpa = (uintptr_t)test_fault_page;
    uintptr_t flags = PTE_V | PTE_U | PTE_A | PTE_D;  /* no R/W/X */
    bool fired = probe_load_gpf(victim_gpa, flags);

    TEST_ASSERT("load guest-page-fault fired", fired);
    TEST_ASSERT_EQ("cause = load guest-page-fault",
                   trap_get_cause(), (uintptr_t)CAUSE_LOAD_GUEST_PAGE_FAULT);

    /* mtval2 value as written by hardware at M-mode trap entry. */
    uintptr_t mtval2 = trap_get_htval();

    /* Strict: exactly 0 or GPA>>2, nothing else. */
    TEST_ASSERT("mtval2 == 0 or GPA>>2 (strict)",
                mtval2 == 0 || mtval2 == (victim_gpa >> 2));

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * MTVAL-03: mtval2 = 0 on non-guest-page-fault trap
 *
 * norm:mtval2_trapval: for other traps, mtval2 is set to zero.
 * ------------------------------------------------------------------ */
TEST_REGISTER(mtval2_non_gpf_trap);
bool mtval2_non_gpf_trap(void) {
    TEST_BEGIN("MTVAL-03: mtval2=0 on non-guest-page-fault trap");

    trap_expect_begin();
    run_in_vs_mode(vs_exec_ecall, 0);
    TEST_ASSERT("ecall trap fired", trap_was_triggered());
    TEST_ASSERT_EQ("cause = ecall from VS-mode",
                   trap_get_cause(), (uintptr_t)CAUSE_ECALL_FROM_VS);
    trap_expect_end();

    /* mtval2/mtinst are M-level trap state rewritten on every M trap; read the
     * values the framework captured at THIS trap's M-mode entry (on the
     * M-delivery path trap_get_htval()/htinst() reflect mtval2/mtinst) rather
     * than the CSRs, which cannot be read from S(HS)-mode. */
    uintptr_t mtval2 = trap_get_htval();
    TEST_ASSERT_EQ("mtval2 must be 0 on non-GPF trap", mtval2, 0);

    uintptr_t mtinst = trap_get_htinst();
    TEST_ASSERT_EQ("mtinst must be 0 on ecall (standard inst)", mtinst, 0);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * MTVAL-04: mtinst WARL read/write
 *
 * norm:mtinst_val: mtinst is WARL and need only hold the values the
 * implementation may automatically write on a trap. Echo is NOT
 * required; zero must be holdable and readback stable.
 * ------------------------------------------------------------------ */
TEST_REGISTER(mtinst_basic_rw);
bool mtinst_basic_rw(void) {
    TEST_BEGIN("MTVAL-04: mtinst WARL read/write semantics");

    /* mtinst is M-level trap state (see MTVAL-01): run the WARL sequence in one
     * M-mode excursion and assert on the values captured there. */
    run_in_priv(PRIV_M, mtinst_warl_probe, 0);
    TEST_ASSERT_EQ("mtinst must hold zero", g_warl_r0, 0);
    TEST_ASSERT_EQ("mtinst readback must be stable", g_warl_r1a, g_warl_r1b);
    TEST_ASSERT_EQ("mtinst value must persist", g_warl_r2, g_warl_r1a);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * MTVAL-05: mtinst on M-mode guest-page-fault trap
 *
 * mtinst must be either 0 or EXACTLY the transformed instruction of
 * the trapping load (golden value computed per SPEC). Observed via
 * the M-mode trap-entry capture (see MTVAL-02 for why a post-hoc CSR
 * read is not valid here).
 * ------------------------------------------------------------------ */
TEST_REGISTER(mtinst_gpf_trap);
bool mtinst_gpf_trap(void) {
    TEST_BEGIN("MTVAL-05: mtinst on M-mode guest-page-fault trap");

    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t victim_gpa = (uintptr_t)test_fault_page;
    uintptr_t flags = PTE_V | PTE_U | PTE_A | PTE_D;  /* no R/W/X */
    bool fired = probe_load_gpf(victim_gpa, flags);

    TEST_ASSERT("load guest-page-fault fired", fired);
    TEST_ASSERT_EQ("cause = load guest-page-fault",
                   trap_get_cause(), (uintptr_t)CAUSE_LOAD_GUEST_PAGE_FAULT);

    /* check_xtinst_zero_or_golden validates trap_get_htinst(), which
     * on the M-mode delivery path is the hardware-written mtinst. */
    (void)check_xtinst_zero_or_golden(
        "mtinst == 0 or exact transformed load", 0x03UL, victim_gpa);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * MTVAL-06: mtval2 on implicit VS-stage access fault
 *
 * norm:mtval2_trapval_vstrans: when a guest-page fault is caused by
 * an implicit memory access during VS-stage translation, a nonzero
 * mtval2 must be the GPA of the faulting implicit access (the PTE
 * being walked). Combined with norm:H_trap_xtinst_guestpage: if
 * mtval2 != 0 then mtinst must be the read pseudoinstruction.
 * ------------------------------------------------------------------ */
TEST_REGISTER(mtval2_implicit_walk);
bool mtval2_implicit_walk(void) {
    TEST_BEGIN("MTVAL-06: mtval2 on implicit VS-stage walk fault");

    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t test_va = HYP_IMP_TEST_VA;

    uintptr_t pt_gpa = setup_implicit_walk_victim(&ctx, test_va, 0);
    TEST_ASSERT("VS leaf PT page resolved", pt_gpa != 0);
    uintptr_t pte_gpa = pt_gpa + VA_VPN(test_va, 0) * sizeof(uintptr_t);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, vs_load_probe, test_va);
    TEST_ASSERT("implicit walk GPF fired", trap_was_triggered());
    if (trap_was_triggered()) {
        TEST_ASSERT_EQ("cause = load guest-page-fault",
                       trap_get_cause(),
                       (uintptr_t)CAUSE_LOAD_GUEST_PAGE_FAULT);

        /* mtval2 as written at M-mode trap entry (a post-hoc CSR read
         * would see the rewrite caused by the ecall return trap). */
        uintptr_t mtval2 = trap_get_htval();

        /* Strict: zero accepted; nonzero must be the implicit-access
         * GPA >> 2, and then mtinst must be the read pseudoinstruction
         * (zero NOT allowed). */
        TEST_ASSERT("mtval2 == 0 or implicit PTE GPA>>2 (strict)",
                    mtval2 == 0 || mtval2 == (pte_gpa >> 2));
        CHECK_IMPLICIT_FAULT_REPORT(pte_gpa >> 2, HTINST_PSEUDO_READ_RV64);
    }
    trap_expect_end();

    two_stage_cleanup(&ctx);
    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * MTVAL-07: htinst WARL read/write
 *
 * norm:htinst_val: htinst is WARL and need only hold the values the
 * implementation may automatically write to it on a trap (zero is
 * always among them, since every non-reporting trap writes zero).
 * Echo of an arbitrary written value is NOT required; zero must be
 * holdable and the readback of any value must be stable. Same WARL
 * semantics as mtinst (MTVAL-04).
 * ------------------------------------------------------------------ */
TEST_REGISTER(htinst_basic_rw);
bool htinst_basic_rw(void) {
    TEST_BEGIN("MTVAL-07: htinst WARL read/write semantics");

    CSRW(CSR_HTINST, 0);
    uintptr_t r0;
    r0 = CSRR(CSR_HTINST);
    TEST_ASSERT_EQ("htinst must hold zero", r0, 0);

    uintptr_t pattern = 0x9876543210FEDCBAUL;
    uintptr_t r1a, r1b;
    CSRW(CSR_HTINST, pattern);
    r1a = CSRR(CSR_HTINST);
    CSRW(CSR_HTINST, pattern);
    r1b = CSRR(CSR_HTINST);
    TEST_ASSERT_EQ("htinst readback must be stable", r1a, r1b);

    uintptr_t r2;
    r2 = CSRR(CSR_HTINST);
    TEST_ASSERT_EQ("htinst value must persist", r2, r1a);

    CSRW(CSR_HTINST, 0);

    HYP_TEST_END();
}
