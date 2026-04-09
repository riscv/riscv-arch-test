//
// Copyright (C) 2024 Harvey Mudd College & Oklahoma State University, Habib University, UET Lahore
//
// SPDX-License-Identifier: Apache-2.0
///////////////////////////////////////////

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: @EXTENSION_LIST@
# @PARAMS@
# MARCH: @MARCH@
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "@TEST_FILE_NAME@"
#define SIGUPD_COUNT @SIGUPD_COUNT_FROM_TESTGEN@

@EXTRA_DEFINES@
#define rvtest_mtrap_routine
#define rvtest_strap_routine
#define rvtest_dtrap_routine
#define RVTEST_PRIV_TEST

#include "riscv_arch_test.h"

RVTEST_BEGIN

#define SEWMIN 8
#define ELEN 64

#if SEWMIN == 64
    #define SEWSIZE e64
    #define VLESEWMIN vle64.v
    #define RVTEST_SIGUPD_V_SEWMIN(BR, TMPR, AVL, VREG) RVTEST_SIGUPD_V(BR, TMPR, AVL, 64, VREG)
#elif SEWMIN == 32
    #define SEWSIZE e32
    #define VLESEWMIN vle32.v
    #define RVTEST_SIGUPD_V_SEWMIN(BR, TMPR, AVL, VREG) RVTEST_SIGUPD_V(BR, TMPR, AVL, 32, VREG)
#elif SEWMIN == 16
    #define SEWSIZE e16
    #define VLESEWMIN vle16.v
    #define RVTEST_SIGUPD_V_SEWMIN(BR, TMPR, AVL, VREG) RVTEST_SIGUPD_V(BR, TMPR, AVL, 16, VREG)
#else
    #define SEWSIZE e8
    #define VLESEWMIN vle8.v
    #define RVTEST_SIGUPD_V_SEWMIN(BR, TMPR, AVL, VREG) RVTEST_SIGUPD_V(BR, TMPR, AVL, 8, VREG)
#endif
