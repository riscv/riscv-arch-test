/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

#ifndef GSTAGE_TEST_HELPERS_H
#define GSTAGE_TEST_HELPERS_H

/* ===================================================================
 * Shared declarations for all Sv*x4 G-stage test files (.c files
 * included by test_register.c).
 * =================================================================== */

#include "test_framework.h"
#include "vm/vm.h"
#include "hyp/hyp_defs.h"
#include "hyp/hyp_csr.h"
#include "hyp/hyp_priv.h"
#include "hyp/hyp_reset.h"
#include "hyp/hyp_test.h"
#include "hyp/gstage_pt.h"
#include "hyp/two_stage.h"
#include "hyp/test_vs_helpers.h"

/* Linker-provided test-region symbols (see kernel.ld). */
extern uint8_t test_data_area[];
extern uint8_t test_fault_page[];
extern uint8_t test_exec_page[];
extern uint8_t test_exec_target[];
extern uint8_t __vm_test_region_start[];
extern uint8_t __vm_test_region_end[];

/* The test region base address is the start of the .vm_test_region
 * section. It is 2MB-aligned. */
#define TEST_REGION_BASE   ((uintptr_t)__vm_test_region_start)

/* G_FLAGS_RWXU_AD (identity-mapping flags with U=1, since all G-stage
 * accesses are treated as U-mode; norm:H_vm_gpapriv) is provided by
 * common/hyp/gstage_pt.h. Do NOT redefine it locally. */

/* ===================================================================
 * Shared helpers (defined in test_helpers.c) for cross-group reuse.
 * Originally lived in test_pte_valid.c; extracted to break implicit
 * include-order coupling between Group files.
 * =================================================================== */

/* Build a G-stage that:
 *   1. identity-maps low-mem (kernel + UART) at 2MB,
 *   2. identity-maps the .vm_test_region pages at 4KB,
 *   3. installs the caller-supplied flags as the leaf for the 4KB
 *      page that contains victim_gpa.
 *
 * After this returns, the M-mode caller can two_stage_run_in_vs() to
 * trigger the desired fault on victim_gpa. */
void _setup_with_victim(two_stage_ctx_t *ctx,
                        uintptr_t victim_gpa,
                        uintptr_t victim_flags);

/* Run helper(target) inside VS-mode under a G-stage built with the
 * supplied victim flags. Returns true iff a guest-page-fault fires
 * with cause == expected_cause. */
bool _vsfault_check(uintptr_t (*helper)(uintptr_t),
                    uintptr_t target,
                    uintptr_t victim_flags,
                    uintptr_t expected_cause);

#endif /* GSTAGE_TEST_HELPERS_H */
