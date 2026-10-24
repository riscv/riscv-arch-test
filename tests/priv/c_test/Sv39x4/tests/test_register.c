/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/*
 * test_register.c - Sv*x4 G-stage Test Registration
 *
 * All test cases are organized by Group, matching
 * docs/gstage_translation_test_plan.md. Each test file is #included
 * here so that TEST_REGISTER macros place function pointers into the
 * .test_table section for auto-execution.
 *
 * Execution order:
 *   Group 1  (HCSR)    - hgatp CSR field validation
 *   Group 2  (ROOT)    - Root page table 16KB alignment
#if SUITE_HGATP_MODE == HGATP_MODE_SV39X4
 *   Group 3  (MAP)     - Sv39x4 basic mapping (1G/2M/4K)
#elif SUITE_HGATP_MODE == HGATP_MODE_SV48X4
 *   Group 4  (MAP)     - Sv48x4 basic mapping (512G/1G/2M/4K)
#elif SUITE_HGATP_MODE == HGATP_MODE_SV57X4
 *   Group 5  (MAP)     - Sv57x4 basic mapping (1G/2M/4K)
#endif
 *   Group 6  (HIGH)    - GPA high-bit check (must be zero)
 *   Group 7  (VALID)   - PTE validity check (V=0, R=0&W=1)
 *   Group 8  (RWX)     - PTE permission bits
 *   Group 9  (UBIT)    - U-bit always treated as U-mode
 *   Group 10 (AD)      - A/D bit management
 *   Group 11 (ALIGN)   - Superpage alignment verification
 *   Group 12 (GBIT)    - G-bit ignored
 *   Group 13 (FAULT)   - Guest-page-fault reporting
 *   Group 14 (BARE)    - hgatp MODE=Bare trivial translation
 */

#include "test_helpers.h"

/* Group 1  */ #include "test_hgatp_csr.c"
/* Group 2  */ #include "test_root_align.c"
#if SUITE_HGATP_MODE == HGATP_MODE_SV39X4
/* Group 3  */ #include "test_basic_map.c"
#elif SUITE_HGATP_MODE == HGATP_MODE_SV48X4
/* Group 4  */ #include "test_basic_map.c"
#elif SUITE_HGATP_MODE == HGATP_MODE_SV57X4
/* Group 5  */ #include "test_basic_map.c"
#endif
/* Group 6  */ #include "test_gpa_high.c"
/* Group 7  */ #include "test_pte_valid.c"
/* Group 8  */ #include "test_rwx.c"
/* Group 9  */ #include "test_ubit.c"
/* Group 10 */ #include "test_ad.c"
/* Group 11 */ #include "test_align.c"
/* Group 12 */ #include "test_gbit.c"
/* Group 13 */ #include "test_fault_report.c"
/* Group 14 */ #include "test_gstage_bare.c"
