// Copyright (c) 2023. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// -----------
// This file contains test macros for vector tests

#ifndef RISCV_TEST_SUITE_TEST_MACROS_VECTOR_H
#define RISCV_TEST_SUITE_TEST_MACROS_VECTOR_H

// Bits mstatus[10:9] have the vector state
#define MSTATUS_VS_SHIFT 9

#define MSTATUS_VS_OFF     (0x0 << MSTATUS_VS_SHIFT)
#define MSTATUS_VS_INITIAL (0x1 << MSTATUS_VS_SHIFT)
#define MSTATUS_VS_CLEAN   (0x2 << MSTATUS_VS_SHIFT)
#define MSTATUS_VS_DIRTY   (0x3 << MSTATUS_VS_SHIFT)
#define MSTATUS_VS_MASK    (0x3 << MSTATUS_VS_SHIFT)

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

// RVTEST_V_ENABLE enables the vector unit
// Perform the following steps:
// - Set mstatus.vs to OFF
// - Set mstatus.vs to INITIAL
// - Read out vlenb and store in VLENB_CACHE
#define RVTEST_V_ENABLE(VLENB_CACHE, HELPER_GPR)                                               \
    li HELPER_GPR, MSTATUS_VS_MASK ;                                    \
    csrrc zero, mstatus, HELPER_GPR ;                                   \
    li HELPER_GPR, MSTATUS_VS_INITIAL ;                                 \
    csrrs zero, mstatus, HELPER_GPR ;                                   \
    csrr VLENB_CACHE, vlenb ;

// RVTEST_SIGUPD_V(_SIG_BASE, _TMP, AVL, SEW, VREG)
//   _SIG_BASE - Base register for signature region (will be incremented)
//   _TMP      - Temporary integer register
//   AVL       - Application vector length (immediate constant)
//   SEW       - Element width in bits (8, 16, 32, or 64)
//   VREG      - Vector register containing data
// TODO: implement SELFCHECK version
#define RVTEST_SIGUPD_V(_SIG_BASE, _TMP, SEW, OFFSET, VREG)      \
  vse ## SEW ##.v VREG, (_SIG_BASE)                           ;\
  nop                                                         ;\
  nop                                                         ;\
  addi _SIG_BASE, _SIG_BASE, OFFSET

#endif // RISCV_TEST_SUITE_TEST_MACROS_VECTOR_H
