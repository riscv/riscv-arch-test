/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_register.c - Shgatpa Compliance Test Registration
 *
 * Each test file is #included so TEST_REGISTER places the function
 * pointers into the .test_table section for auto-execution by main().
 *
 * Execution order matches DOCS/testplan/shgatpa_test_plan.md:
 *   Group 1  PROBE  - satp MODE support probing (baseline)
 *   Group 2  MODE   - hgatp SvNNx4 consistency with satp
 *   Group 3  BARE   - hgatp Bare mode mandatory support
 *   Group 4  WARL   - hgatp MODE WARL behavior
 *   Group 5  PPN    - hgatp PPN field low 2-bit behavior
 *   Group 6  VMID   - VMID field width
 */

#include "test_framework.h"
#include "hyp/hyp_test.h"
#include "hyp/hyp_csr.h"
#include "hyp/hyp_defs.h"

/* Group 1 */ #include "test_probe.c"
/* Group 2 */ #include "test_mode.c"
/* Group 3 */ #include "test_bare.c"
/* Group 4 */ #include "test_warl.c"
/* Group 5 */ #include "test_ppn.c"
/* Group 6 */ #include "test_vmid.c"
