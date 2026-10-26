/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_register.c - Hypervisor × Svinval Cross Test Registration
 *
 * All test cases are organized by Group, matching
 * DOCS/testplan/Hypervisor_cross_test_plan.md Group 5.
 *
 * Each test file is #included here so TEST_REGISTER macros place
 * function pointers into the .test_table section for auto-execution
 * by main().
 *
 * Execution order:
 *   Group 5 (HCROSS-SINVAL) - Hypervisor × Svinval cross tests
 */

#include "test_helpers.h"

/* --- Group 5: Hypervisor × Svinval (HCROSS-SINVAL-01~15) --- */
#include "test_hcross_svinval.c"
