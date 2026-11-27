/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * main.c - Shgatpa Extension Compliance Test entry point
 *
 * See DOCS/testplan/shgatpa_test_plan.md for the full test plan.
 *
 * The Shgatpa extension requires:
 *   (1) For every satp SvNN, hgatp SvNNx4 must be supported.
 *   (2) hgatp Bare mode must always be supported.
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

    test_print_banner("RISC-V Shgatpa Extension Compliance Test");

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
