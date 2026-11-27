/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#include "test_framework.h"

#include "act4_compat.h"

#ifdef ENABLE_HYP
#include "hyp_reset.h"      /* hyp_misa_h */
#include "hyp_vs_trap.h"    /* vs_trap_setup_framework */
#endif

/* Runtime CSR access (defined in csr_accessors.c) */
extern uintptr_t csr_read(uint16_t csr);
extern void csr_write(uint16_t csr, uintptr_t val);

/* ===================================================================
 * Test result tracking (global)
 * =================================================================== */
test_result_t test_results = {
    .total = 0,
    .passed = 0,
    .failed = 0,
    .skipped = 0,
    .tests_passed = 0,
    .tests_failed = 0,
    .current_test_name = NULL,
    .current_test_failed = false,
    .failed_names = {0},
    .failed_count = 0,
    .skipped_names = {0},
    .skipped_reasons = {0},
    .skipped_count = 0,
};

/* ===================================================================
 * reset_state - Reset common test state to clean baseline
 *
 * Only performs common resets. Extension-specific resets
 * (e.g., pmp_reset, smepmp_reset) should be called separately.
 * =================================================================== */

/* Gate for the CFI / Pointer-Masking cleanup in reset_state() and for the
 * trap-armed helper it uses. Expressed purely with capabilities.h
 * <EXT>_AVAILABLE macros (no local aggregate macro, no ENABLE_* build flag):
 * the cleanup exists solely for bits owned by Zicfilp/Zicfiss/Smnpm/Ssnpm/
 * Smmpm, so a platform declaring none of them compiles both out -- which also
 * keeps the unused static helper from triggering -Wunused-function. */
#if ZICFILP_AVAILABLE || ZICFISS_AVAILABLE || \
    SMNPM_AVAILABLE   || SSNPM_AVAILABLE   || SMMPM_AVAILABLE
/* ===================================================================
 * _safe_csr_clear_field - trap-protected CSR field clearing
 *
 * Reads a CSR by runtime address, clears the bits specified by
 * @mask, and writes back.  The read is trap-protected so that
 * accessing a non-existent CSR is safe (the write is skipped).
 * Reusable for any extension that needs conditional CSR cleanup
 * in reset paths (Pointer Masking, Zicfilp/Zicfiss, ...).
 * =================================================================== */
static void _safe_csr_clear_field(uint16_t csr, uintptr_t mask) {
    trap_expect_begin();
    uintptr_t val = csr_read(csr);
    if (!trap_was_triggered()) {
        csr_write(csr, val & ~mask);
    }
    trap_expect_end();
}
#endif /* ZICFILP/ZICFISS/SMNPM/SSNPM/SMMPM available */

void reset_state(void) {
    /* Ensure we're in M-mode */
    if (get_current_priv() != PRIV_M)
        goto_priv(PRIV_M);

    /* Reset trap state — clear ALL fields, not just armed.
     * This prevents stale trap_was_triggered()/trap_get_cause() results
     * from a previous test leaking into the next one. */
    trap_clear_record();

    /* Set up trap vectors */
    extern void m_trap_entry(void);
    extern void s_trap_entry(void);
    CSRW(mtvec, (uintptr_t)m_trap_entry);
    CSRW(stvec, (uintptr_t)s_trap_entry);

#ifdef ENABLE_HYP
    /* And the third level, for the same reason the other two are here rather
     * than only at boot: the delegation baseline applied below hands ordinary
     * V=1 stimulus to the VS handler, so that handler has to be reachable
     * before any test runs.  Without it a delegated trap would be "delivered"
     * to vstvec = 0, fault on the fetch, be delegated again by the same bit and
     * spin at PC 0 with no output at all.
     *
     * Guarded at runtime as well as at compile time: a suite may be built with
     * ENABLE_HYP and still run on a part without H, where vstvec does not
     * exist. */
    if (hyp_misa_h())
        vs_trap_setup_framework();
#endif

    /* Detect mtval2 CSR availability (H-extension / double-trap
     * platforms only). Must run after trap vectors are installed.
     * The probe itself may record a trap, so re-clear the record
     * afterwards to keep a clean baseline for the tests. */
    trap_probe_mtval2();
    trap_clear_record();

    /* Restore the delegation-first baseline (NOT zero).
     *
     * S-mode-normal model: stimulus traps are meant to be delivered
     * straight to the S handler, and ecall-from-S must stay undelegated so
     * the T-SBI service channel keeps working.  A test that needs the
     * "undelegated leg" switches a cause out with trap_undelegate_exc()
     * and gets it restored here. */
    tsbi_deleg_restore_baseline();

    /* Ensure interrupts are disabled */
    CSRC(mstatus, MSTATUS_MIE_BIT | MSTATUS_SIE_BIT);

    /* Clear interrupt enable registers to prevent residual enable bits
     * from triggering unexpected traps when a later test re-enables MIE.
     * mstatus.MIE/SIE only gates the global interrupt; individual enables
     * in mie/sie persist across tests and can fire immediately if mip
     * has pending bits (e.g., after mret restores MIE=MPIE). */
    CSRW(mie, 0);
    CSRW(sie, 0);

    /* Clear software-writable pending interrupt bits in mip.
     * Read-only bits (MTIP, MEIP, STIP) are unaffected by writes.
     * Writable bits: SSIP (1), MSIP (3), SEIP (9), LCOFIP (13). */
    CSRW(mip, 0);

    /* Clear mstatus bits that could affect subsequent tests:
     * - MPRV (bit 17): M-mode using translated addresses
     * - SUM  (bit 18): S-mode accessing U=1 pages without explicit intent
     * - MXR  (bit 19): may alter load access permissions
     * - TVM  (bit 20): S-mode satp/hgatp access restriction
     * - TSR  (bit 22): S-mode sret restriction */
    CSRC(mstatus, MSTATUS_MPRV_BIT | MSTATUS_SUM_BIT |
                  MSTATUS_MXR_BIT  | MSTATUS_TVM_BIT |
                  MSTATUS_TSR_BIT);

    /* Clear Smdbltrp MDT if supported (no-op otherwise).
     * MDT is set by hardware on M-mode trap entry; if left set,
     * the next EXPECT_TRAP in M-mode triggers a fatal double trap. */
    clear_mdt();

    /* Clear Zicfilp/Zicfiss enforcement AND Pointer-Masking (PMM) so every
     * suite starts from a clean baseline regardless of which extensions it
     * is built with. A previous suite can leave these enable bits set, and
     * a suite not built with ENABLE_HYP / ENABLE_PM / CFI cannot clear them
     * itself, so without a hart reset they leak into the next suite:
     *   - menvcfg.LPE/SSE: a Hypervisor henvcfg test sets menvcfg.LPE to
     *     make henvcfg.LPE writable and only clears henvcfg afterwards;
     *     the leak makes an S-mode indirect jump landing on a non-`lpad`
     *     target raise a software-check exception (mcause=18, mtval=2/3).
     *   - menvcfg/senvcfg/mseccfg.PMM (Smnpm/Ssnpm/Smmpm): a pointer-
     *     masking (Zpm) test leaves PMM!=0; the leak masks and sign-extends
     *     S/U/M-mode effective addresses in the next suite (e.g. an amocas
     *     target 0x0000_8000_xxxx becomes 0xffff_8000_xxxx -> wrong access
     *     -> page fault / double trap, mcause=16).
     *
     * Each field is gated on the PLATFORM capability declaration
     * (<EXT>_AVAILABLE, capabilities.h), NOT on this suite's own ENABLE_PM /
     * ENABLE_HYP build flags: whether a leaked PMM/LPE can exist at all is a
     * property of the DUT, not of how one suite was compiled. Capability
     * gating therefore still cleans the leak for a suite built without
     * ENABLE_PM (the flag comes from config/<platform>/rvtest_config.h, which
     * every suite of that platform shares), while dropping the trap-armed CSR
     * probe on platforms that declare none of these extensions -- see
     * capabilities.h design note 5 (support is declaration-driven, never
     * runtime-probed). Nothing is left uncleaned by the narrower gate: a bit
     * can only be set on a DUT that declares the extension owning it.
     *
     * The read-modify-write stays trap-armed because the *cfg CSR itself may
     * be absent where the field's extension is declared (e.g. Zicfilp without
     * Smenvcfg). mseccfg.PMM may be sticky on some implementations; a
     * silently failed write there is acceptable. */
#if ZICFILP_AVAILABLE || ZICFISS_AVAILABLE || \
    SMNPM_AVAILABLE   || SSNPM_AVAILABLE   || SMMPM_AVAILABLE
    {
        uintptr_t menvcfg_clr = 0;
        uintptr_t senvcfg_clr = 0;
        uintptr_t mseccfg_clr = 0;

#if ZICFILP_AVAILABLE
        menvcfg_clr |= MENVCFG_LPE;
        senvcfg_clr |= SENVCFG_LPE;
        mseccfg_clr |= MSECCFG_MLPE;
#endif
#if ZICFISS_AVAILABLE
        menvcfg_clr |= MENVCFG_SSE;
        senvcfg_clr |= SENVCFG_SSE;
#endif
#if SMNPM_AVAILABLE
        menvcfg_clr |= MENVCFG_PMM_MASK;
#endif
#if SSNPM_AVAILABLE
        senvcfg_clr |= SENVCFG_PMM_MASK;
#endif
#if SMMPM_AVAILABLE
        mseccfg_clr |= MSECCFG_PMM_MASK;
#endif

        if (menvcfg_clr)
            _safe_csr_clear_field(CSR_MENVCFG, menvcfg_clr);
        if (senvcfg_clr)
            _safe_csr_clear_field(CSR_SENVCFG, senvcfg_clr);
        if (mseccfg_clr)
            _safe_csr_clear_field(CSR_MSECCFG, mseccfg_clr);
    }
#endif /* ZICFILP/ZICFISS/SMNPM/SSNPM/SMMPM available */

#if ZICFILP_AVAILABLE
    /* MPELP is a WARL mstatus bit, so a plain clear is safe. */
    CSRC(mstatus, MSTATUS_MPELP_BIT);
#endif

#ifdef ENABLE_HYP
    /* Clear mstatus.MPV to prevent stale virtualization state.
     * If a previous test entered VS/VU mode and left MPV=1,
     * subsequent mret could unintentionally enter V=1 mode. */
    CSRC(mstatus, MSTATUS_MPV);
#endif

    /* Disable address translation (satp = bare mode).
     * Prevents a previous test's page table from remaining active
     * when a subsequent test enters S-mode. */
    CSRW(satp, 0);

#ifdef ENABLE_PM
    /* Clear Pointer Masking (PM) state via the generic helper.
     * senvcfg.PMM [33:32] (Ssnpm), menvcfg.PMM [33:32] (Smnpm),
     * mseccfg.PMM [33:32] (Smmpm).
     * Only needed when PM extension is enabled. */
    _safe_csr_clear_field(CSR_SENVCFG, SENVCFG_PMM_MASK);
    _safe_csr_clear_field(CSR_MENVCFG, MENVCFG_PMM_MASK);
    /* mseccfg.PMM may be sticky on some implementations;
     * the write may silently fail, which is acceptable. */
    _safe_csr_clear_field(CSR_MSECCFG, MSECCFG_PMM_MASK);
#endif /* ENABLE_PM */

    /* Last clean-slate sweep, for the same reason as after the mtval2 probe
     * above: every trap-protected probe in this function leaves the record
     * dirty.  trap_expect_begin() clears it on entry but trap_expect_end()
     * only disarms, so a probe of a CSR the platform lacks (mseccfg on
     * Spike, say) leaves triggered=true behind, and the first test to assert
     * !trap_was_triggered() fails on a trap it never caused. */
    trap_clear_record();

#ifndef TSBI_BOOT_MODE_M
    /* Back to the S-mode normal state.
     *
     * Everything above needs M-mode authority, so reset_state() raises
     * privilege on entry (goto_priv(PRIV_M) at the top) and hands control
     * back to S here - one raise and one drop per reset, rather than one
     * trap round trip per M-CSR.
     *
     * Lowering privilege does not involve T-SBI (see the design brief's
     * "raising is a request, lowering is a right"). */
    goto_priv(PRIV_S);
#endif
}

/* ===================================================================
 * test_print_banner - Print test suite banner
 * =================================================================== */
void test_print_banner(const char *title)
{
    printf("\n");
    printf("==============================================\n");
    printf("  %s\n", title);
    printf("==============================================\n");
    printf("  Platform:     %s\n", CONFIG_NAME);
    printf("  XLEN:         %d\n", __riscv_xlen);
    printf("  Compiler:     %s\n", COMPILER_INFO);
    printf("  MEM_BASE:     0x%lx\n", (unsigned long)PLATFORM_MEM_BASE);
    printf("  MEM_SIZE:     0x%lx\n", (unsigned long)PLATFORM_MEM_SIZE);
    printf("==============================================\n\n");
}

/* ===================================================================
 * test_print_summary - Print final test results
 * =================================================================== */
int test_print_summary(void) {
    unsigned int tests_total = test_results.tests_passed +
                               test_results.tests_failed +
                               test_results.skipped;

    printf("\n========================================\n");
    printf("  Test Summary\n");
    printf("========================================\n");
    printf("  Total:   %u\n", tests_total);
    printf("  Passed:  %u\n", test_results.tests_passed);
    printf("  Failed:  %u\n", test_results.tests_failed);
    printf("  Skipped: %u\n", test_results.skipped);
    printf("----------------------------------------\n");
    printf("  Assertions: %u total, %u passed, %u failed\n",
           test_results.total, test_results.passed, test_results.failed);

    if (test_results.skipped > 0) {
        printf("----------------------------------------\n");
        printf("  Skipped tests:\n");
        for (unsigned int i = 0; i < test_results.skipped_count; i++) {
            printf("    %u) %s: %s\n", i + 1,
                   test_results.skipped_names[i],
                   test_results.skipped_reasons[i]);
        }
        if (test_results.skipped > test_results.skipped_count) {
            printf("    ... and %u more\n",
                   test_results.skipped - test_results.skipped_count);
        }
    }

    printf("========================================\n");
    if (test_results.tests_failed == 0 && test_results.skipped == 0) {
        printf("  RESULT: ALL PASSED\n");
    } else if (test_results.tests_failed == 0) {
        printf("  RESULT: ALL PASSED (%u tests skipped)\n",
               test_results.skipped);
    } else {
        printf("  RESULT: %u FAILURES\n", test_results.tests_failed);
        printf("----------------------------------------\n");
        printf("  Failed tests:\n");
        for (unsigned int i = 0; i < test_results.failed_count; i++) {
            printf("    %u) %s\n", i + 1, test_results.failed_names[i]);
        }
        if (test_results.tests_failed > test_results.failed_count) {
            printf("    ... and %u more\n",
                   test_results.tests_failed - test_results.failed_count);
        }
    }

    printf("========================================\n\n");

    int failed = (int)test_results.tests_failed;
    act4_report_summary(failed);
    return failed;
}
