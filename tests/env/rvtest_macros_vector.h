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

#endif // RISCV_TEST_SUITE_TEST_MACROS_VECTOR_H
