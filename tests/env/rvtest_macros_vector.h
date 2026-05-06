// Copyright (c) 2023. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// -----------
// This file contains test macros for vector tests

#ifndef RISCV_TEST_SUITE_TEST_MACROS_VECTOR_H
#define RISCV_TEST_SUITE_TEST_MACROS_VECTOR_H

// Define which LMUL fractions are supported based on SEW_MIN and ELEN
#if SEW_MIN == 8
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
        #error "ELEN unsupported, check SEW_MIN"
    #endif
#elif SEW_MIN == 16
    #if ELEN == 64
        #define LMULf4_SUPPORTED
        #define LMULf2_SUPPORTED
    #elif ELEN == 32
        #define LMULf2_SUPPORTED
    #elif ELEN == 16
    #else
        #error "ELEN unsupported, check SEW_MIN"
    #endif
#elif SEW_MIN == 32
    #if ELEN == 64
        #define LMULf2_SUPPORTED
    #elif ELEN == 32
    #else
        #error "ELEN unsupported, check SEW_MIN"
    #endif
#endif

// Per-test fractional LMUL support based on RVTEST_SEW (set in each test) and ELEN.
// The testgen-emitted #if guards in the test source run BEFORE this header is included,
// at which point ELEN is still undefined, so the test-source defines never fire.
// Defining them here (after ELEN is in scope) ensures #ifdef TEST_LMULfN_SUPPORTED
// in the test body works correctly.
#if defined(RVTEST_SEW) && defined(ELEN)
    #if (RVTEST_SEW <= ELEN / 2)
        #ifndef TEST_LMULf2_SUPPORTED
            #define TEST_LMULf2_SUPPORTED
        #endif
    #endif
    #if (RVTEST_SEW <= ELEN / 4)
        #ifndef TEST_LMULf4_SUPPORTED
            #define TEST_LMULf4_SUPPORTED
        #endif
    #endif
    #if (RVTEST_SEW <= ELEN / 8)
        #ifndef TEST_LMULf8_SUPPORTED
            #define TEST_LMULf8_SUPPORTED
        #endif
    #endif
#endif


#endif // RISCV_TEST_SUITE_TEST_MACROS_VECTOR_H
