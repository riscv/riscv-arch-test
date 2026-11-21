/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * Test Group 4: htinst/mtinst transformed instructions
 *
 * Tests TINST-01 through TINST-10 verify htinst/mtinst behavior on
 * traps, following the strict-verification principles of the test
 * plan (DOCS/testplan/Hypervisor_Exceptions_test_plan.md, Group 4):
 *  - zero is always accepted where the spec allows it;
 *  - any nonzero value must EXACTLY match the spec-derived golden
 *    value (transformed instruction computed from the trapping
 *    instruction at mepc, or the mandated pseudoinstruction);
 *  - implicit VS-stage walk faults with htval != 0 require the
 *    pseudoinstruction value; zero is NOT allowed there.
 */

#include "hyp_test_helpers.h"

/* mie/hvip bit for the VS software interrupt (VSSIP/VSSIE). */
#define VS_SOFT_INT_BIT   (1UL << 2)

/* ------------------------------------------------------------------
 * TINST-01: Interrupt trap writes zero to the trap instruction CSR
 *
 * norm:H_trap_xtinst_interrupt: on an interrupt, the value written to
 * mtinst/htinst is ALWAYS zero.
 *
 * A VS software interrupt is injected via hvip.VSSIP. Per
 * norm:mideleg_acc_h, mideleg bits 2/6/10 are read-only 1, so a
 * VS-level interrupt can never trap to M-mode; with hideleg bit 2
 * clear it is delivered to HS-mode and htinst is observed there.
 *
 * The test installs _hs_trap_entry as the HS-mode stvec handler so
 * that the interrupt is captured at HS-mode. The HS-mode trap
 * handler records htinst, cause, htval and SPV for verification.
 * ------------------------------------------------------------------ */
TEST_REGISTER(htinst_interrupt_zero);
bool htinst_interrupt_zero(void) {
    TEST_BEGIN("TINST-01: Verify htinst=0 during an interrupt trap");

    /* hideleg.VSSIP must be clear so the interrupt traps to HS-mode
     * (not VS-mode). */
    uintptr_t hideleg = hideleg_read();
    hideleg_write(hideleg & ~VS_SOFT_INT_BIT);
    CSRW(CSR_HVIP, 0);

    uintptr_t saved_hie;
    saved_hie = CSRR(CSR_HIE);

    /* Save stvec and install HS-mode trap handler. */
    uintptr_t saved_stvec;
    saved_stvec = CSRR(CSR_STVEC);
    CSRW(CSR_STVEC, (uintptr_t)&_hs_trap_entry);

    /* Reset the HS-mode trap record. */
    hs_trap_record_reset();

    /* Enable only VSSIE via hie. */
    CSRW(CSR_HIE, VS_SOFT_INT_BIT);

    /* Ensure vsstatus.SIE=1 so the interrupt fires when V=1. */
    uintptr_t saved_vsstatus;
    saved_vsstatus = CSRR(CSR_VSSTATUS);
    CSRW(CSR_VSSTATUS, saved_vsstatus | 0x2);

    /* (removed) The old "set mstatus.MPIE=1 so SIE=1 after mret into VS-mode"
     * is obsolete under S-mode-normal: mstatus is M-level (the raw csrr/csrs
     * trap from S(HS)-mode -- here they were silently skipped by the installed
     * HS handler, leaving saved_mstatus uninitialized), MPIE is a return-path
     * bit, and every framework excursion re-enters VS via mret (MPIE<-1). It is
     * also unnecessary: VS-level interrupt delivery is gated by vsstatus.SIE
     * (set above) + hie + hvip.VSSIP, not by mstatus.MIE/MPIE (which only gate
     * interrupts while executing in M-mode). */

    /* Inject VSSIP; it fires during VS-mode execution. */
    CSRS(CSR_HVIP, VS_SOFT_INT_BIT);

    /* Enter VS-mode. The VSSIP traps to HS-mode (hideleg[2]=0,
     * mideleg[2]=1). The HS handler records htinst, clears hvip,
     * and returns via sret. VS-mode then completes the ecall
     * round-trip back to M-mode. */
    run_in_vs_mode(vs_nop_fn, 0);

    /* Restore state. */
    CSRW(CSR_HVIP, 0);
    CSRW(CSR_HIE, saved_hie);
    CSRW(CSR_STVEC, saved_stvec);
    CSRW(CSR_VSSTATUS, saved_vsstatus);
    hideleg_write(hideleg);

    TEST_ASSERT("interrupt trap fired", hs_trap_was_triggered());
    TEST_ASSERT_EQ("cause = VS software interrupt",
                   hs_trap_get_cause(), CAUSE_INTERRUPT_BIT | IRQ_VS_SOFTWARE);
    TEST_ASSERT("trap came from V=1 (hstatus.SPVP at entry)",
                trap_get_spv());
    TEST_ASSERT_EQ("htinst must be 0 on interrupt (strict)",
                   hs_trap_get_htinst(), 0);
    TEST_ASSERT_EQ("htval must be 0 on interrupt (strict)",
                   hs_trap_get_htval(), 0);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * TINST-02: ECALL trap writes zero to htinst
 *
 * tinst-values table: for Environment call, only Zero may be written
 * (a custom value is allowed only for non-standard instructions, and
 * ecall is standard). Hence htinst == 0 strictly.
 * ------------------------------------------------------------------ */
TEST_REGISTER(htinst_ecall_zero);
bool htinst_ecall_zero(void) {
    TEST_BEGIN("TINST-02: Verify htinst=0 during ECALL trap (strict)");

    trap_expect_begin();
    run_in_vs_mode(vs_exec_ecall, 0);
    TEST_ASSERT("ecall trap fired", trap_was_triggered());
    TEST_ASSERT_EQ("cause = ecall from VS-mode",
                   trap_get_cause(), (uintptr_t)CAUSE_ECALL_FROM_VS);
    trap_expect_end();

    TEST_ASSERT_EQ("htinst must be 0 on ecall (strict)",
                   trap_get_htinst(), 0);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * TINST-03: Load guest-page-fault htinst value
 *
 * A deterministic VS-mode `ld` faults on a G-stage leaf without read
 * permission. htinst must be either 0 (always allowed) or EXACTLY the
 * transformed load computed from the trapping instruction.
 * ------------------------------------------------------------------ */
TEST_REGISTER(htinst_load_gpf);
bool htinst_load_gpf(void) {
    TEST_BEGIN("TINST-03: htinst on load guest-page-fault (0 or golden)");

    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t victim_gpa = (uintptr_t)test_fault_page;
    /* G-stage leaf: readable NOT (no R/W/X) -> load guest-page-fault. */
    uintptr_t flags = PTE_V | PTE_U | PTE_A | PTE_D;
    bool fired = probe_load_gpf(victim_gpa, flags);

    TEST_ASSERT("load guest-page-fault fired", fired);
    TEST_ASSERT_EQ("cause = load guest-page-fault",
                   trap_get_cause(), (uintptr_t)CAUSE_LOAD_GUEST_PAGE_FAULT);

    (void)check_xtinst_zero_or_golden(
        "htinst == 0 or exact transformed load", 0x03UL, victim_gpa);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * TINST-04: Store guest-page-fault htinst value
 * ------------------------------------------------------------------ */
TEST_REGISTER(htinst_store_gpf);
bool htinst_store_gpf(void) {
    TEST_BEGIN("TINST-04: htinst on store guest-page-fault (0 or golden)");

    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t victim_gpa = (uintptr_t)test_fault_page;
    /* G-stage leaf: R but NOT W -> store guest-page-fault. */
    uintptr_t flags = PTE_V | PTE_R | PTE_U | PTE_A | PTE_D;
    bool fired = probe_store_gpf(victim_gpa, flags);

    TEST_ASSERT("store guest-page-fault fired", fired);
    TEST_ASSERT_EQ("cause = store guest-page-fault",
                   trap_get_cause(), (uintptr_t)CAUSE_STORE_GUEST_PAGE_FAULT);

    (void)check_xtinst_zero_or_golden(
        "htinst == 0 or exact transformed store", 0x23UL, victim_gpa);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * TINST-05: Implicit VS-stage read fault pseudoinstruction
 *
 * The VS-stage leaf page-table page is made unreadable at G-stage, so
 * the PTE walk raises a guest-page-fault on an implicit read.
 * norm:H_trap_xtinst_guestpage: when htval != 0, htinst MUST be the
 * read pseudoinstruction 0x00003000 (RV64) — zero is NOT allowed.
 * ------------------------------------------------------------------ */
TEST_REGISTER(htinst_implicit_vs_fault);
bool htinst_implicit_vs_fault(void) {
    TEST_BEGIN("TINST-05: htinst pseudoinstruction on implicit VS-stage read fault");

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
        /* Strict: htval == 0 accepted; if nonzero, htval must be the
         * implicit-access GPA>>2 and htinst the read pseudoinstruction
         * (zero NOT allowed). */
        CHECK_IMPLICIT_FAULT_REPORT(pte_gpa >> 2, HTINST_PSEUDO_READ_RV64);
    }
    trap_expect_end();

    two_stage_cleanup(&ctx);
    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * TINST-06: Implicit write (A/D update) pseudoinstruction
 *
 * The VS-stage leaf page-table page carries D=0 at G-stage. Without
 * ADUE, the walker's implicit A/D write faults there; htinst must be
 * the WRITE pseudoinstruction 0x00003020 (RV64) when htval != 0.
 * Platforms auto-updating A/D (Svadu) never raise the fault: SKIP.
 * ------------------------------------------------------------------ */
TEST_REGISTER(htinst_ad_update);
bool htinst_ad_update(void) {
    TEST_BEGIN("TINST-06: htinst write pseudoinstruction on implicit A/D update fault");

    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t test_va = HYP_IMP_TEST_VA;

    uintptr_t pt_gpa = setup_implicit_walk_victim(
        &ctx, test_va, G_FLAGS_RWXU_AD & ~PTE_D);
    TEST_ASSERT("VS leaf PT page resolved", pt_gpa != 0);
    uintptr_t pte_gpa = pt_gpa + VA_VPN(test_va, 0) * sizeof(uintptr_t);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, vs_load_probe, test_va);
    bool fired = trap_was_triggered();
    trap_expect_end();

    if (!fired) {
        two_stage_cleanup(&ctx);
        TEST_SKIP("platform auto-updates A/D (Svadu), no implicit write GPF");
    }

    /* Cause follows the original access type (load). */
    TEST_ASSERT_EQ("cause = load guest-page-fault",
                   trap_get_cause(),
                   (uintptr_t)CAUSE_LOAD_GUEST_PAGE_FAULT);
    CHECK_IMPLICIT_FAULT_REPORT(pte_gpa >> 2, HTINST_PSEUDO_WRITE_RV64);

    two_stage_cleanup(&ctx);
    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * TINST-07: Transformed instruction field-by-field structure
 *
 * Same scenario as TINST-03; when htinst is nonzero every field is
 * checked individually against the SPEC transformed-load format:
 * opcode/funct3/rd preserved, immediate zeroed, Addr. Offset correct,
 * bits 1:0 = 11 for a non-compressed instruction.
 * ------------------------------------------------------------------ */
TEST_REGISTER(htinst_bits_encoding);
bool htinst_bits_encoding(void) {
    TEST_BEGIN("TINST-07: transformed instruction field structure");

    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t victim_gpa = (uintptr_t)test_fault_page;
    uintptr_t flags = PTE_V | PTE_U | PTE_A | PTE_D;
    bool fired = probe_load_gpf(victim_gpa, flags);

    TEST_ASSERT("load guest-page-fault fired", fired);
    TEST_ASSERT_EQ("cause = load guest-page-fault",
                   trap_get_cause(), (uintptr_t)CAUSE_LOAD_GUEST_PAGE_FAULT);

    uintptr_t htinst = check_xtinst_zero_or_golden(
        "htinst == 0 or exact transformed load", 0x03UL, victim_gpa);

    if (htinst != 0) {
        uintptr_t epc  = trap_get_epc();
        uintptr_t inst = hyp_fetch_inst32(epc);

        TEST_ASSERT_EQ("bits 1:0 = 11 (non-compressed)", htinst & 3UL, 3UL);
        TEST_ASSERT_EQ("opcode preserved",
                       htinst & 0x7FUL, inst & 0x7FUL);
        TEST_ASSERT_EQ("funct3 preserved",
                       (htinst >> 12) & 7UL, (inst >> 12) & 7UL);
        TEST_ASSERT_EQ("rd preserved",
                       (htinst >> 7) & 0x1FUL, (inst >> 7) & 0x1FUL);
        TEST_ASSERT_EQ("immediate field zeroed",
                       htinst & 0xFFF00000UL, 0UL);

        uintptr_t tval = trap_get_tval();
        uintptr_t off  = (tval != 0 && tval >= victim_gpa)
                         ? (tval - victim_gpa) : 0;
        TEST_ASSERT_EQ("Addr. Offset field",
                       (htinst >> 15) & 0x1FUL, off & 0x1FUL);
    }

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * TINST-08: Compressed instruction transformed encoding
 *
 * norm:H_trap_xtinst_exception: for a standard COMPRESSED trapping
 * instruction the transformed value is found by (1) expanding to the
 * 32-bit equivalent, (2) transforming that instruction, (3) replacing
 * bit 1 with 0 -- so bits 1:0 = 01 mark a compressed source
 * (hypervisor.adoc, "Transformed Instruction").
 * A 2-byte `c.lw a0, 0(a0)` (0x4108) faults on a G-stage leaf
 * without read permission; htinst must be 0 (always allowed) or
 * exactly that compressed transformed value.
 * ------------------------------------------------------------------ */
TEST_REGISTER(htinst_compressed_encoding);
bool htinst_compressed_encoding(void) {
    TEST_BEGIN("TINST-08: Verify compressed instruction transformed encoding");

#if !defined(__riscv_compressed)
    TEST_SKIP("C extension not available in this test build");
#endif

    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    uintptr_t victim_gpa = (uintptr_t)test_fault_page;
    /* G-stage leaf: readable NOT (no R/W/X) -> load guest-page-fault. */
    uintptr_t flags = PTE_V | PTE_U | PTE_A | PTE_D;
    bool fired = probe_load_gpf_c(victim_gpa, flags);

    TEST_ASSERT("load guest-page-fault fired", fired);
    TEST_ASSERT_EQ("cause = load guest-page-fault",
                   trap_get_cause(), (uintptr_t)CAUSE_LOAD_GUEST_PAGE_FAULT);

    /* The trapping instruction at mepc must be the compressed c.lw. */
    uintptr_t epc  = trap_get_epc();
    uintptr_t half = *(volatile uint16_t *)epc;
    TEST_ASSERT("trapping inst is compressed (bits 1:0 != 11)",
                (half & 3UL) != 3UL);
    TEST_ASSERT_EQ("compressed inst is c.lw a0, 0(a0)", half, 0x4108UL);

    /* Golden value: expanded equivalent is `lw a0, 0(a0)` =
     * 0x00052503; transform it, then replace bit 1 with 0. */
    uintptr_t tval = trap_get_tval();
    uintptr_t off  = (tval != 0 && tval >= victim_gpa)
                     ? (tval - victim_gpa) : 0;
    uintptr_t golden = hyp_transform_mem_inst(0x00052503UL, off) & ~2UL;
    TEST_ASSERT("golden transformed value computable", golden != 0);

    uintptr_t val = trap_get_htinst();
    if (!(val == 0 || val == golden)) {
        LOG_W("TINST-08: trap-inst-reg=0x%lx golden=0x%lx "
              "tval=0x%lx\n",
              (unsigned long)val, (unsigned long)golden,
              (unsigned long)tval);
    }
    TEST_ASSERT("htinst == 0 or transformed uncompressed equivalent",
                val == 0 || val == golden);

    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * TINST-09: VS-stage page fault does not produce a pseudoinstruction
 *
 * A VS-stage leaf PTE without R raises a plain load page-fault
 * (cause 13, NOT a guest-page fault). tinst-values table: load page
 * fault allows Zero or a transformed instruction only — never a
 * pseudoinstruction.
 * ------------------------------------------------------------------ */
TEST_REGISTER(htinst_page_fault_no_pseudo);
bool htinst_page_fault_no_pseudo(void) {
    TEST_BEGIN("TINST-09: page-fault htinst is 0 or transformed (no pseudoinst)");

    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);

    two_stage_ctx_t ctx;
    gpt_pool_reset();
    two_stage_init(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE);

    uintptr_t lo_base = PLATFORM_MEM_BASE & ~(PAGE_SIZE_2M - 1);
    uintptr_t r_start = (uintptr_t)__vm_test_region_start;
    uintptr_t lo_end  = r_start & ~(PAGE_SIZE_2M - 1);

    /* VS-stage: low region RWX; test_data_area mapped WITHOUT R so a
     * VS-mode load raises a VS-stage load page-fault (cause 13). */
    two_stage_vs_identity(&ctx, lo_base, lo_end - lo_base,
                          PTE_V | PTE_R | PTE_W | PTE_X | PTE_A | PTE_D,
                          PT_LEVEL_2M);
    uintptr_t target = (uintptr_t)test_data_area;
    two_stage_vs_map(&ctx, target, target,
                     PTE_V | PTE_W | PTE_X | PTE_U | PTE_A | PTE_D,
                     PT_LEVEL_4K);

    /* G-stage: identity RWX everywhere. */
    uintptr_t r_end = (uintptr_t)__vm_test_region_end;
    two_stage_setup_identity(&ctx, lo_base, r_end - lo_base,
                             G_FLAGS_RWXU_AD, PT_LEVEL_4K);

    trap_expect_begin();
    (void)two_stage_run_in_vs(&ctx, vs_load_probe, target);
    TEST_ASSERT("VS-stage page fault fired", trap_was_triggered());
    if (trap_was_triggered()) {
        TEST_ASSERT_EQ("cause = load page fault (13)",
                       trap_get_cause(), (uintptr_t)CAUSE_LOAD_PAGE_FAULT);

        uintptr_t htinst = check_xtinst_zero_or_golden(
            "htinst == 0 or exact transformed load", 0x03UL, target);

        /* Explicit: pseudoinstruction values are illegal here. */
        TEST_ASSERT("htinst must not be a pseudoinstruction",
                    htinst != HTINST_PSEUDO_READ_RV64 &&
                    htinst != HTINST_PSEUDO_WRITE_RV64);
    }
    trap_expect_end();

    two_stage_cleanup(&ctx);
    HYP_TEST_END();
}

/* ------------------------------------------------------------------
 * TINST-10: illegal-instruction trap allows only zero
 *
 * tinst-values table: for Illegal instruction, Transformed = No,
 * Custom = No (custom values are reserved for non-standard trapping
 * instructions), Pseudoinstruction = No. Hence htinst must be 0.
 * ------------------------------------------------------------------ */
TEST_REGISTER(htinst_illegal_zero);
bool htinst_illegal_zero(void) {
    TEST_BEGIN("TINST-10: htinst=0 on illegal-instruction trap (strict)");

    trap_expect_begin();
    run_in_vs_mode(vs_exec_illegal, 0);
    TEST_ASSERT("illegal-inst trap fired", trap_was_triggered());
    TEST_ASSERT_EQ("cause = illegal-instruction",
                   trap_get_cause(), (uintptr_t)CAUSE_ILLEGAL_INST);
    trap_expect_end();

    TEST_ASSERT_EQ("htinst must be 0 on illegal-instruction (strict)",
                   trap_get_htinst(), 0);

    HYP_TEST_END();
}
