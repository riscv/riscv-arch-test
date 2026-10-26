/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * main.c - Hypervisor Interrupts Compliance Test entry point
 *
 * See DOCS/testplan/Hypervisor_Interrupts_test_plan.md for the full test plan.
 *
 * This suite covers the H-extension interrupt behaviour including:
 *   - Virtual interrupt injection (hvip/hip/hie)
 *   - Guest external interrupts (hgeip/hgeie)
 *   - M-level interrupt delegation enhancements (mideleg/mip/mie)
 *   - hideleg interrupt delegation and VS interrupt number translation
 */

#include "test_framework.h"
#include "vm/vm.h"
#include "hyp/hyp_defs.h"
#include "hyp/hyp_reset.h"
#include "hyp/hyp_csr.h"

extern test_func_t _test_table[];
extern test_func_t _test_table_end[];

int main(void) {
    uart_init();
    reset_state();

    test_print_banner("RISC-V Hypervisor Interrupts Compliance Test");

    unsigned int test_count = (unsigned int)(
        (uintptr_t)_test_table_end - (uintptr_t)_test_table
    ) / sizeof(test_func_t);


    /* Clean H-ext baseline before the first test. */
    hyp_reset_state();

    /* Open the Sstc timer-compare gate for the whole suite. Several cases
     * drive stimecmp/vstimecmp from S(HS)-mode (the VS-timer neutralization in
     * setup_vs_int_test and HINT-06/17/18/21). From HS-mode those CSRs are
     * reachable only when menvcfg.STCE=1, and spike additionally gates the
     * S-mode timer-compare access on mcounteren.TM. Platform reset values
     * differ (QEMU tends to reset STCE=1 with the comparators armed, spike
     * resets STCE=0), so enable the gate once here and disarm both comparators,
     * putting the timer-driven STIP/VSTIP into a known quiescent state on every
     * platform. Neither reset_state() nor hyp_reset_state() clears
     * menvcfg.STCE or mcounteren.TM, so this persists across tests. The
     * disarming writes are trap-guarded so a platform without Sstc (STCE
     * read-only-zero) simply skips them instead of taking an illegal-instruction
     * trap into the framework handler. */
    tsbi_csr_set(CSR_MENVCFG, MENVCFG_STCE);
    tsbi_csr_set(CSR_MCOUNTEREN, 1U << 1);   /* TM: allow HS-mode time / stimecmp access */
    trap_expect_begin();
    CSRW(CSR_STIMECMP, (uintptr_t)-1);
    CSRW(CSR_VSTIMECMP, (uintptr_t)-1);
    trap_expect_end();
    trap_clear_record();

    for (unsigned int i = 0; i < test_count; i++) {
        _test_table[i]();
    }

    return test_print_summary();
}
