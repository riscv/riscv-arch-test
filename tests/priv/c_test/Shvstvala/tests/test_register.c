/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_register.c - Shvstvala Test Registration File
 *
 * All test cases are organized by Group, matching shvstvala_test_plan.md.
 * Each test file is #included here so TEST_REGISTER macros place
 * function pointers into the .test_table section for auto-execution.
 *
 * Execution order:
 *   Group 1 (PF)      - Page-fault vstval = faulting VA
 *   Group 2 (AF)      - Access-fault vstval = faulting VA
 *   Group 3 (MA)      - Misaligned vstval = faulting VA
 *   Group 4 (ILL)     - Illegal instruction vstval = instruction encoding
 *   Group 5 (TRANS)   - vstval transparent VS<->M read/write
 *   Group 6 (BRK)     - Breakpoint vstval = faulting address
 */

#include "shvstvala_helpers.h"

/* --- Group 1: Page-Fault (VSTVAL-LPF/SPF/IPF) --- */
#include "test_pagefault.c"

/* --- Group 2: Access-Fault (VSTVAL-LAF/SAF/IAF) --- */
#include "test_accessfault.c"

/* --- Group 3: Misaligned (VSTVAL-IMA/LMA/SMA) --- */
#include "test_misaligned.c"

/* --- Group 4: Illegal Instruction (VSTVAL-ILL) --- */
#include "test_illegal.c"

/* --- Group 5: vstval Transparent (VSTVAL-TRANS) --- */
#include "test_transparent.c"

/* --- Group 6: Breakpoint (VSTVAL-BRK) --- */
#include "test_breakpoint.c"
