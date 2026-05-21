// Copyright (c) 2023. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// -----------
// This file contains test macros for vector tests

#ifndef RISCV_TEST_SUITE_TEST_MACROS_VECTOR_H
#define RISCV_TEST_SUITE_TEST_MACROS_VECTOR_H

// Define which LMUL fractions are supported based on UDB_SEW_MIN and UDB_ELEN
#if UDB_SEW_MIN == 8
    #if UDB_ELEN == 64
        #define LMULf8_SUPPORTED
        #define LMULf4_SUPPORTED
        #define LMULf2_SUPPORTED
    #elif UDB_ELEN == 32
        #define LMULf4_SUPPORTED
        #define LMULf2_SUPPORTED
    #elif UDB_ELEN == 16
        #define LMULf2_SUPPORTED
    #elif UDB_ELEN == 8
    #else
        #error "UDB_ELEN unsupported, check UDB_SEW_MIN"
    #endif
#elif UDB_SEW_MIN == 16
    #if UDB_ELEN == 64
        #define LMULf4_SUPPORTED
        #define LMULf2_SUPPORTED
    #elif UDB_ELEN == 32
        #define LMULf2_SUPPORTED
    #elif UDB_ELEN == 16
    #else
        #error "UDB_ELEN unsupported, check UDB_SEW_MIN"
    #endif
#elif UDB_SEW_MIN == 32
    #if UDB_ELEN == 64
        #define LMULf2_SUPPORTED
    #elif UDB_ELEN == 32
    #else
        #error "UDB_ELEN unsupported, check UDB_SEW_MIN"
    #endif
#endif

// Per-test fractional LMUL support based on RVTEST_SEW (set in each test) and UDB_ELEN.
// The testgen-emitted #if guards in the test source run BEFORE this header is included,
// at which point UDB_ELEN is still undefined, so the test-source defines never fire.
// Defining them here (after UDB_ELEN is in scope) ensures #ifdef TEST_LMULfN_SUPPORTED
// in the test body works correctly.
#if defined(RVTEST_SEW) && defined(UDB_ELEN)
    #if (RVTEST_SEW <= UDB_ELEN / 2)
        #ifndef TEST_LMULf2_SUPPORTED
            #define TEST_LMULf2_SUPPORTED
        #endif
    #endif
    #if (RVTEST_SEW <= UDB_ELEN / 4)
        #ifndef TEST_LMULf4_SUPPORTED
            #define TEST_LMULf4_SUPPORTED
        #endif
    #endif
    #if (RVTEST_SEW <= UDB_ELEN / 8)
        #ifndef TEST_LMULf8_SUPPORTED
            #define TEST_LMULf8_SUPPORTED
        #endif
    #endif
#endif


#endif // RISCV_TEST_SUITE_TEST_MACROS_VECTOR_H
