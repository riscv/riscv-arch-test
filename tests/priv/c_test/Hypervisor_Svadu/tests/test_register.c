/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_register.c - Hypervisor × Svadu Cross Test Registration
 *
 * All test cases are organized by Group, matching
 * DOCS/testplan/Hypervisor_cross_test_plan.md Group 1.
 *
 * Each test file is #included here so TEST_REGISTER macros place
 * function pointers into the .test_table section for auto-execution
 * by main().
 *
 * Execution order:
 *   Group 1 (HCROSS-SVADU) - Hypervisor × Svadu cross tests
 */

#include "test_helpers.h"

/* --- Group 1: Hypervisor × Svadu (HCROSS-SVADU-01~06) --- */
#include "test_hcross_svadu.c"
