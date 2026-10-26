/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * main.c - Hypervisor × Svinval Cross Test entry point
 *
 * See DOCS/testplan/Hypervisor_cross_test_plan.md Group 5.
 *
 * This suite verifies the interaction between the Hypervisor (H)
 * extension and the Svinval extension (fine-grained TLB invalidation):
 *   - HINVAL.VVMA / HINVAL.GVMA functionality
 *   - VMID semantics for HINVAL.GVMA
 *   - VS/VU-mode virtual-instruction exceptions for HINVAL
 *   - SFENCE.W.INVAL / SFENCE.INVAL.IR ordering
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

    test_print_banner("Hypervisor x Svinval Cross Test");

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
