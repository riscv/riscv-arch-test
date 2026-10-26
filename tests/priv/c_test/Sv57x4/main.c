/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#include "test_framework.h"
#include "vm/vm.h"
#include "hyp/hyp_defs.h"
#include "hyp/hyp_reset.h"

extern test_func_t _test_table[];
extern test_func_t _test_table_end[];

int main(void) {
    uart_init();
    reset_state();

#if SUITE_HGATP_MODE == HGATP_MODE_SV39X4
    test_print_banner("RISC-V Sv39x4 G-stage Translation Compliance Test");
#elif SUITE_HGATP_MODE == HGATP_MODE_SV48X4
    test_print_banner("RISC-V Sv48x4 G-stage Translation Compliance Test");
#elif SUITE_HGATP_MODE == HGATP_MODE_SV57X4
    test_print_banner("RISC-V Sv57x4 G-stage Translation Compliance Test");
#else
    test_print_banner("RISC-V Sv*x4 G-stage Translation Compliance Test");
#endif

    unsigned int test_count = (unsigned int)(
        (uintptr_t)_test_table_end - (uintptr_t)_test_table
    ) / sizeof(test_func_t);


    /* Make sure all H-ext state is in a clean baseline before the
     * first test. */
    hyp_reset_state();

    for (unsigned int i = 0; i < test_count; i++) {
        _test_table[i]();
    }

    return test_print_summary();
}
