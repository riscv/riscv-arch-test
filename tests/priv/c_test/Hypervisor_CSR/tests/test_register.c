/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_register.c - Hypervisor CSR Compliance Test Registration
 *
 * All test cases are organized by Group, matching
 * DOCS/testplan/Hypervisor_CSR_test_plan.md.
 *
 * Each test file is #included here so TEST_REGISTER macros place
 * function pointers into the .test_table section for auto-execution
 * by main().
 *
 * Execution order:
 *   Group  1  VCSR   - VS CSR substitution
 *   Group  2  HSTAT  - hstatus register
 *   Group  3  HENV   - henvcfg configuration
 *   Group  4  HTDL   - htimedelta time offset
 *   Group  5  VSST   - vsstatus register
 *   Group  6  VSIE   - vsip/vsie alias verification
 *   Group  7  VSTC   - vstimecmp timer
 *   Group  8  VSCR   - vsscratch/vsepc/vscause/vstval
 *   Group  9  DELEG  - hedeleg/hideleg field constraints
 */

#include "hyp_test_helpers.h"
#include "cmo/cmo.h"

/* Group 1 */ #include "test_csr_basics.c"
/* Group 2 */ #include "test_hstatus.c"
/* Group 3 */ #include "test_henvcfg.c"
/* Group 4 */ #include "test_htimedelta.c"
/* Group 5 */ #include "test_vsstatus.c"
/* Group 6 */ #include "test_vsip_vsie.c"
/* Group 7 */ #include "test_vstimecmp.c"
/* Group 8 */ #include "test_vs_scratch.c"
/* Group 9 */ #include "test_deleg_csr.c"
