/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_register.c - Shtvala Compliance Test Registration
 *
 * Each test file is #included so TEST_REGISTER places the function
 * pointers into the .test_table section for auto-execution by main().
 *
 * Execution order matches DOCS/testplan/shtvala_test_plan.md:
 *   Group 1  REG  - htval CSR existence / WARL
 *   Group 2  EXP  - explicit G-stage GPF (load/store/fetch)
 *   Group 3  IMP  - implicit VS-stage PTE GPF        [SKIP placeholder]
 *   Group 4  STR  - straddle / cross-page accesses
 *   Group 5  HLV  - HLV/HLVX/HSV from HS-mode        [SKIP placeholder]
 *   Group 6  MOD  - hgatp.MODE coverage (Sv39x4/48x4/57x4)
 *   Group 7  CLR  - non-GPF traps must NOT modify htval
 *   Group 8  CON  - htval / stval consistency (low-bit reconstruction)
 *   Group 9  GVA  - hstatus.GVA linkage with htval
 */

#include "test_helpers.h"

/* Group 1 */ #include "test_htval_reg.c"
/* Group 2 */ #include "test_htval_explicit.c"
/* Group 3 */ #include "test_htval_implicit.c"
/* Group 4 */ #include "test_htval_straddle.c"
/* Group 5 */ #include "test_htval_hlv.c"
/* Group 6 */ #include "test_htval_modes.c"
/* Group 7 */ #include "test_htval_clear.c"
/* Group 8 */ #include "test_htval_consistency.c"
/* Group 9 */ #include "test_htval_gva.c"
