/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * main.c - Hypervisor Exceptions Compliance Test entry point
 *
 * See DOCS/testplan/Hypervisor_Exceptions_test_plan.md for the full test plan.
 *
 * This suite covers the H-extension exception and trap behaviour including:
 *   - Virtual-instruction exception (cause=22)
 *   - Trap entry/return behaviour under H-extension
 *   - htinst/mtinst transformed instructions
 *   - mstatus enhancements (MPV/GVA/TVM/MPRV)
 *   - mtval2/mtinst registers
 *   - Exception priority
 *   - hedeleg exception delegation chain
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

    test_print_banner("RISC-V Hypervisor Exceptions Compliance Test");

    unsigned int test_count = (unsigned int)(
        (uintptr_t)_test_table_end - (uintptr_t)_test_table
    ) / sizeof(test_func_t);


    /* Clean H-ext baseline before the first test; every test clears H state
     * again on its way out, including through TEST_SKIP/TEST_FATAL (see the
     * TEST_EXIT_RESET override in common/hyp/hyp_test.h). */
    hyp_reset_state();

    /* VINST-31 exercises VS-mode access to henvcfg and needs it HS-qualified
     * so the access raises a virtual-instruction (cause=22) rather than an
     * illegal-instruction (cause=2). Under Smstateen that qualification is
     * gated by mstateen0.ENVCFG, which spike resets to 0, so open the gate once
     * here (hyp_reset_state does not clear mstateen0, so it persists across
     * tests). Not folded into the shared baseline: the Smstateen/Ssstateen
     * suites test that gate and set it themselves. */
    hyp_enable_envcfg_access();

    for (unsigned int i = 0; i < test_count; i++) {
        _test_table[i]();
    }

    return test_print_summary();
}
