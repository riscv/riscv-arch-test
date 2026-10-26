/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * main.c - Hypervisor × Svadu Cross Test entry point
 *
 * See DOCS/testplan/Hypervisor_cross_test_plan.md Group 1.
 *
 * This suite verifies the interaction between the Hypervisor (H)
 * extension and the Svadu extension (Hardware Update of PTE A/D bits)
 * in two-stage address translation scenarios:
 *   - henvcfg.ADUE writability
 *   - HLV/HSV instructions with hardware A/D update
 *   - menvcfg.ADUE modification and HFENCE.GVMA synchronization
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

    test_print_banner("Hypervisor x Svadu Cross Test");

    unsigned int test_count = (unsigned int)(
        (uintptr_t)_test_table_end - (uintptr_t)_test_table
    ) / sizeof(test_func_t);


    /* Clean H-ext baseline before the first test. */
    hyp_reset_state();

    /* This suite drives henvcfg.ADUE from S(HS)-mode (via ts2_enable_adue ->
     * henvcfg_set_adue -> henvcfg_read/write). Under Smstateen henvcfg is
     * gated by mstateen0.ENVCFG, which spike resets to 0, so a direct HS-mode
     * henvcfg access would raise an illegal instruction. Open the gate once
     * here (hyp_reset_state does not clear mstateen0, so it persists across
     * tests). Not done in the shared baseline: the Smstateen/Ssstateen suites
     * test that gate and set it themselves. */
    hyp_enable_envcfg_access();

    for (unsigned int i = 0; i < test_count; i++) {
        _test_table[i]();
    }

    return test_print_summary();
}
