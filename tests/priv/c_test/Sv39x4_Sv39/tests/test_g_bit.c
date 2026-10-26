/*
 * Copyright (c) 2026 Alibaba Group.
 * SPDX-License-Identifier: Apache-2.0
 */

/* ===================================================================
 * common/hyp/tests_2stage/test_group17_g_bit.c
 *
 * Group 17 - G-stage PTE G bit ignored (TS-GBIT-01).
 *
 * Spec basis (norm:H_vm_gpa_g): The G bit (PTE bit 5) is currently
 * unused by G-stage; software is expected to write zero, hardware is
 * required to ignore it.
 * =================================================================== */

#ifndef SUITE_HGATP_MODE
#error "SUITE_HGATP_MODE must be defined before including this file"
#endif
#ifndef SUITE_VSATP_MODE
#error "SUITE_VSATP_MODE must be defined before including this file"
#endif


#define G17_VS_FULL       (PTE_V|PTE_R|PTE_W|PTE_X|PTE_A|PTE_D)
#define G17_G_FULL_GBIT   (PTE_V|PTE_R|PTE_W|PTE_X|PTE_U|PTE_A|PTE_D|PTE_G)

TEST_REGISTER(test_ts_gbit_01_ignored);
bool test_ts_gbit_01_ignored(void) {
    TEST_BEGIN("TS-GBIT-01: G-stage PTE G=1 -> ignored, translation OK");
    REQUIRE_VSATP_MODE(SUITE_VSATP_MODE);
    REQUIRE_HGATP_MODE(SUITE_HGATP_MODE);

    two_stage_ctx_t ctx;
    uintptr_t va = (uintptr_t)test_data_area;
    /* G-stage leaf carries G=1 plus full RWXU AD; VS-stage is normal. */
    ts2_setup_with_dual_victim(&ctx, SUITE_VSATP_MODE, SUITE_HGATP_MODE,
                               va, G17_VS_FULL, G17_G_FULL_GBIT);

    uintptr_t r = ts2_run_check_no_fault(&ctx, test_vs_read_write, va);
    TEST_ASSERT("two-stage RW succeeds with G-stage PTE G=1", r == 0);
    HYP_TEST_END();
}
