/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * main.c - Hypervisor x Svnapot Cross Test entry point
 *
 * See DOCS/testplan/Hypervisor_cross_test_plan.md Group 6.
 *
 * This suite verifies the Svnapot extension (NAPOT PTE) behavior
 * in Hypervisor G-stage translation scenarios:
 *   - G-stage 64 KiB NAPOT basic translation
 *   - G-stage NAPOT reserved encoding fault
 *   - Both VS-stage and G-stage using NAPOT simultaneously
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

    test_print_banner("Hypervisor x Svnapot Cross Test");

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
