/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_register.c - Sha (Augmented Hypervisor) Compliance Test Registration
 *
 * Each test file is #included so TEST_REGISTER places the function
 * pointers into the .test_table section for auto-execution by main().
 *
 * Execution order matches DOCS/testplan/sha_test_plan.md:
 *   Group 1  EXIST       - Sub-extension existence smoke tests
 *   Group 2  STATEEN     - Ssstateen CSR basic accessibility
 *   Group 3  HCTL        - hstateen VS/VU access control
 *   Group 4  HIER        - mstateen->hstateen->sstateen hierarchy
 *   Group 5  CROSS       - Cross-extension interaction
 *   Group 6  PRIO        - Exception priority
 */

#include "test_framework.h"
#include "hyp/hyp_test.h"
#include "hyp/hyp_csr.h"
#include "hyp/hyp_defs.h"
#include "hyp/hyp_priv.h"
#include "hyp/hyp_trap.h"
#include "hyp/two_stage.h"
#include "hyp/gstage_pt.h"

/* Group 1 */ #include "test_exist.c"
/* Group 2 */ #include "test_stateen.c"
/* Group 3 */ #include "test_hctl.c"
/* Group 4 */ #include "test_hierarchy.c"
/* Group 5 */ #include "test_cross.c"
/* Group 6 */ #include "test_priority.c"
