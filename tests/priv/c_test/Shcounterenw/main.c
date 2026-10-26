/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * main.c - Shcounterenw Extension Compliance Test entry point
 *
 * See DOCS/testplan/shcounterenw_test_plan.md for the full test plan.
 *
 * The Shcounterenw extension specifies that:
 *   For any hpmcounter that is NOT read-only zero, the corresponding
 *   hcounteren bit MUST be writable.
 *
 * Group 1: M-mode hcounteren bit writability verification
 * Group 2: VS-mode end-to-end access control
 * Group 3: hcounteren bit toggle consistency
 * Group 4: mcounteren/hcounteren/scounteren hierarchy interaction
 * Group 5: read-only zero counter report
 */

#include "test_framework.h"
#include "hyp/hyp_defs.h"
#include "hyp/hyp_reset.h"

extern test_func_t _test_table[];
extern test_func_t _test_table_end[];

int main(void) {
    uart_init();
    reset_state();

    test_print_banner("RISC-V Shcounterenw Extension Compliance Test");

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
