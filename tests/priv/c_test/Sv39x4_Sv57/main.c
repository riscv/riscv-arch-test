/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
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

    test_print_banner("RISC-V Sv57 + Sv39x4 Two-Stage Translation Test");

    printf("  VS-stage:     Sv57\n");
    printf("  G-stage:      Sv39x4\n");
    unsigned int test_count = (unsigned int)(
        (uintptr_t)_test_table_end - (uintptr_t)_test_table
    ) / sizeof(test_func_t);


    hyp_reset_state();

    /* The shared tests read henvcfg/menvcfg from HS-mode (TS-PBMTE and
     * the Svadu capability check in test_implicit_gstage_fault.c).
     * With Smstateen implemented, mstateen0.ENVCFG=0 (a common reset
     * default) makes any henvcfg/senvcfg access from below M trap as
     * an illegal instruction. Open the gate once here; this suite
     * does not test the stateen gate itself. Contained to this
     * suite's setup: the global baseline is untouched so the
     * Smstateen/Ssstateen/Ssnpm suites still observe the gate
     * closed. */
    hyp_enable_envcfg_access();

    for (unsigned int i = 0; i < test_count; i++) {
        _test_table[i]();
    }

    return test_print_summary();
}
