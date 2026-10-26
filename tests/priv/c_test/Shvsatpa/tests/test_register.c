/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_register.c - Shvsatpa Compliance Test Registration
 *
 * Each test file is #included so TEST_REGISTER places the function
 * pointers into the .test_table section for auto-execution by main().
 *
 * Execution order matches DOCS/testplan/shvsatpa_test_plan.md:
 *   Group 1  PROBE  - satp MODE support probing (baseline)
 *   Group 2  MODE   - vsatp MODE consistency with satp (V=0)
 *   Group 3  VS     - VS-mode satp instruction verification
 *   Group 4  TRANS  - V=1 transparent semantics
 *   Group 5  UNSUP  - unsupported MODE write handling
 *   Group 6  ASID   - ASID field width consistency
 */

#include "test_framework.h"
#include "hyp/hyp_test.h"
#include "hyp/hyp_csr.h"
#include "hyp/hyp_priv.h"
#include "hyp/hyp_defs.h"
#include "hyp/two_stage.h"
#include "hyp/gstage_pt.h"

/* Group 1 */ #include "test_probe.c"
/* Group 2 */ #include "test_mode.c"
/* Group 3 */ #include "test_vsmode.c"
/* Group 4 */ #include "test_transparent.c"
/* Group 5 */ #include "test_unsupported.c"
/* Group 6 */ #include "test_asid.c"
