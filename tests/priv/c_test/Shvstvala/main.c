/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * main.c - Shvstvala Extension Compliance Test entry point
 *
 * See DOCS/testplan/shvstvala_test_plan.md for the full test plan.
 *
 * The Shvstvala extension specifies that vstval must be written with
 * the same values Sstvala mandates for stval, when a trap enters VS-mode:
 *   - Address exceptions: vstval = faulting virtual address
 *   - Illegal instruction: vstval = faulting instruction encoding
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

    test_print_banner("RISC-V Shvstvala Extension Compliance Test");

    unsigned int test_count = (unsigned int)(
        (uintptr_t)_test_table_end - (uintptr_t)_test_table
    ) / sizeof(test_func_t);


    /* Clean H-ext baseline before the first test. */
    hyp_reset_state();

    for (unsigned int i = 0; i < test_count; i++) {
        _test_table[i]();
    }

    return test_print_summary();
}
