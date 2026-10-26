/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * main.c - Shvstvecd Extension Compliance Test entry point
 *
 * See DOCS/testplan/shvstvecd_test_plan.md for the full test plan.
 *
 * The Shvstvecd extension specifies that:
 *   (1) vstvec.MODE must be capable of holding 0 (Direct).
 *   (2) When vstvec.MODE=Direct, vstvec.BASE must hold any valid
 *       four-byte-aligned address.
 *
 * Groups 1 & 2 operate entirely in M-mode on CSR 0x205 (vstvec).
 * Groups 3-5 use run_in_vs_mode() to exercise VS-mode trap behavior.
 */

#include "test_framework.h"
#include "hyp/hyp_defs.h"
#include "hyp/hyp_reset.h"

extern test_func_t _test_table[];
extern test_func_t _test_table_end[];

int main(void) {
    uart_init();
    reset_state();

    test_print_banner("RISC-V Shvstvecd Extension Compliance Test");

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
