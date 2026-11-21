/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * main.c - Hypervisor CSR Compliance Test entry point
 *
 * See DOCS/testplan/Hypervisor_CSR_test_plan.md for the full test plan.
 *
 * This suite covers the H-extension CSR behaviour including:
 *   - VS CSR substitution and hstatus behaviour
 *   - Environment configuration (henvcfg/htimedelta)
 *   - VS CSRs (vsstatus/vsip/vsie/vstimecmp/vsscratch/vsepc/vscause/vstval)
 *   - hedeleg/hideleg register field constraints
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

    test_print_banner("RISC-V Hypervisor CSR Compliance Test");

    unsigned int test_count = (unsigned int)(
        (uintptr_t)_test_table_end - (uintptr_t)_test_table
    ) / sizeof(test_func_t);


    /* Clean H-ext baseline before the first test. */
    hyp_reset_state();

    /* This suite manipulates henvcfg/senvcfg from S(HS)-mode. Under Smstateen
     * those are gated by mstateen0.ENVCFG, which spike resets to 0, so open the
     * gate once here (hyp_reset_state does not clear mstateen0, so it persists
     * across tests). Not done in the shared baseline: the Smstateen/Ssstateen
     * suites test that gate and set it themselves. */
    hyp_enable_envcfg_access();

    for (unsigned int i = 0; i < test_count; i++) {
        _test_table[i]();
    }

    return test_print_summary();
}
