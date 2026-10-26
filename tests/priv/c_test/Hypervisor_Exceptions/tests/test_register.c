/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_register.c - Hypervisor Exceptions Compliance Test Registration
 *
 * All test cases are organized by Group, matching
 * DOCS/testplan/Hypervisor_Exceptions_test_plan.md.
 *
 * Each test file is #included here so TEST_REGISTER macros place
 * function pointers into the .test_table section for auto-execution
 * by main().
 *
 * Execution order:
 *   Group  1  VINST  - virtual-instruction exception
 *   Group  2  TENT   - trap entry behaviour
 *   Group  3  TRET   - trap return behaviour
 *   Group  4  TINST  - htinst/mtinst transformed instructions
 *   Group  5  MSTAT  - mstatus hypervisor enhancements
 *   Group  6  MTVAL  - mtval2/mtinst registers
 *   Group  7  PRIO   - exception priority
 *   Group  8  DELEG  - hedeleg exception delegation chain
 */

#include "hyp_test_helpers.h"

/* Group 1 */ #include "test_virtual_inst.c"
/* Group 2 */ #include "test_trap_entry.c"
/* Group 3 */ #include "test_trap_return.c"
/* Group 4 */ #include "test_htinst.c"
/* Group 5 */ #include "test_mstatus_hyp.c"
/* Group 6 */ #include "test_mtval2.c"
/* Group 7 */ #include "test_exception_priority.c"
/* Group 8 */ #include "test_deleg_exception.c"
