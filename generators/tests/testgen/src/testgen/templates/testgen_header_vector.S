///////////////////////////////////////////
// @TEST_PATH@
// Copyright (C) 2025 Harvey Mudd College & Oklahoma State University, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
///////////////////////////////////////////

##### START_TEST_CONFIG #####
# implemented_extensions: @EXTENSION_LIST@
# params:
#   MXLEN: @XLEN@
# MARCH: @MARCH@
# CONFIG_DEPENDENT: @CONFIG_DEPENDENT@
##### END_TEST_CONFIG #####

// TODO: add params: MVLEN, ELEN, SEWMIN

// Define special purpose registers before including test_macros_vector.h
#define DATA_BASE x4
#define SIG_BASE x3
#define VLENB_CACHE x5
#define HELPER_GPR x6
#define SEW@SEW@

#define SIGUPD_COUNT 500 // TODO: change
#include "test_macros_vector.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN
RVTEST_V_ENABLE()

#define SEWMIN 8
#define ELEN 64
#define MAXINDEXEEW 64

#if SEWMIN == 8
    #if ELEN == 64
        #define LMULf8_SUPPORTED
        #define LMULf4_SUPPORTED
        #define LMULf2_SUPPORTED
    #elif ELEN == 32
        #define LMULf4_SUPPORTED
        #define LMULf2_SUPPORTED
    #elif ELEN == 16
        #define LMULf2_SUPPORTED
    #elif ELEN == 8
    #else
        #error "ELEN unsupported, check SEWMIN"
    #endif
#elif SEWMIN == 16
    #if ELEN == 64
        #define LMULf4_SUPPORTED
        #define LMULf2_SUPPORTED
    #elif ELEN == 32
        #define LMULf2_SUPPORTED
    #elif ELEN == 16
    #else
        #error "ELEN unsupported, check SEWMIN"
    #endif
#elif SEWMIN == 32
    #if ELEN == 64
        #define LMULf2_SUPPORTED
    #elif ELEN == 32
    #else
        #error "ELEN unsupported, check SEWMIN"
    #endif
#endif
