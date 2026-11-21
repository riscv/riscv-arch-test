/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_register.c - Shcounterenw Test Registration File
 *
 * All test cases are organized by Group, matching shcounterenw_test_plan.md.
 * Each test file is #included here so TEST_REGISTER macros place
 * function pointers into the .test_table section for auto-execution.
 *
 * Execution order:
 *   Group 1 (WR)      - hcounteren bit writability verification
 *   Group 2 (ACCESS)  - VS-mode access control (end-to-end)
 *   Group 3 (TOGGLE)  - hcounteren bit toggle consistency
 *   Group 4 (HIER)    - mcounteren/hcounteren/scounteren hierarchy
 *   Group 5 (RO)      - read-only zero counter report
 */

#include "shcounterenw_helpers.h"

/* --- Group 1: hcounteren Writability (SHCNTW-WR-01 ~ WR-04) --- */
#include "test_writable.c"

/* --- Group 2: VS-mode Access Control (SHCNTW-ACCESS-01 ~ ACCESS-08) --- */
#include "test_access.c"

/* --- Group 3: Toggle Consistency (SHCNTW-TOGGLE-01 ~ TOGGLE-03) --- */
#include "test_toggle.c"

/* --- Group 4: Hierarchy Interaction (SHCNTW-HIER-01 ~ HIER-05) --- */
#include "test_hierarchy.c"

/* --- Group 5: Read-only Zero Report (SHCNTW-RO-01) --- */
#include "test_readonly.c"
