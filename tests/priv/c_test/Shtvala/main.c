/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * main.c - Shtvala Extension Compliance Test entry point
 *
 * See DOCS/testplan/shtvala_test_plan.md for the full test plan.
 *
 * The Shtvala extension specifies that on a guest-page-fault the
 * implementation MUST write htval = (faulting GPA) >> 2. This
 * suite delegates nothing to HS (hedeleg = 0), so all
 * guest-page-faults are taken in M-mode and the trap framework
 * exposes mtval2/mtinst/mstatus.GVA as trap_get_htval/htinst/gva.
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

    test_print_banner("RISC-V Shtvala Extension Compliance Test");

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
