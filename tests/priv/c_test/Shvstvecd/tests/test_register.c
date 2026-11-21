/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_register.c - Shvstvecd Extension Test Registration
 *
 * All Shvstvecd test cases are organized by Group, matching
 * DOCS/testplan/shvstvecd_test_plan.md. Each test file is #included
 * here so the TEST_REGISTER macros place function pointers into the
 * .test_table section for auto-execution by main.c.
 *
 * Execution order:
 *   Group 1 (MODE)        - vstvec.MODE writability           (2 cases)
 *   Group 2 (BASE)        - vstvec.BASE holding capacity      (7 cases)
 *   Group 3 (DIRECT)      - MODE=Direct VS trap dispatch      (4 cases)
 *   Group 4 (TRANSPARENT) - V=1 transparency                  (3 cases)
 *   Group 5 (VECTORED)    - Vectored mode probe               (2 cases)
 */

#include "test_helpers.h"

/* --- Group 1: vstvec.MODE writability (VSTVEC-MODE-01~02) --- */
#include "test_mode.c"

/* --- Group 2: vstvec.BASE holding capacity (VSTVEC-BASE-01~08) --- */
/* Note: BASE-05 was removed from the plan; 7 cases total. */
#include "test_base.c"

/* --- Group 3: MODE=Direct VS trap dispatch (VSTVEC-DIR-01~03, INT-01) --- */
#include "test_direct.c"

/* --- Group 4: V=1 transparency (VSTVEC-TRANS-01~03) --- */
#include "test_transparent.c"

/* --- Group 5: Vectored mode probe (VSTVEC-VEC-01~02) --- */
#include "test_vectored.c"
