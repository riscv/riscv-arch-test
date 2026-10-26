/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_register.c - Hypervisor Interrupts Compliance Test Registration
 *
 * All test cases are organized by Group, matching
 * DOCS/testplan/Hypervisor_Interrupts_test_plan.md.
 *
 * Each test file is #included here so TEST_REGISTER macros place
 * function pointers into the .test_table section for auto-execution
 * by main().
 *
 * Execution order:
 *   Group  1  HINT   - hvip/hip/hie interrupts        (test_interrupts.c)
 *   Group  2  HGEI   - hgeip/hgeie guest external     (test_interrupts.c)
 *   Group  3  MIDLG  - mideleg/mip/mie enhancements
 *   Group  4  DELEG  - hideleg interrupt delegation and translation
 */

#include "hyp_test_helpers.h"

/* Group 1-2 */ #include "test_interrupts.c"
/* Group 3   */ #include "test_mideleg_enhance.c"
/* Group 4   */ #include "test_deleg_interrupt.c"
