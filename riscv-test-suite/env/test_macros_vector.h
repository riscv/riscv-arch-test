// Copyright (c) 2023. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// -----------
// This file contains test macros for vector tests

#ifndef RISCV_TEST_SUITE_TEST_MACROS_VECTOR_H
#define RISCV_TEST_SUITE_TEST_MACROS_VECTOR_H

#include "model_test.h"
#include "arch_test.h"

// We require four GPRs to be reserved for special purposes:
// - SIG_BASE: Base address of signature memory region
//   Used by *SIGUPD_V* macros
// - DATA_BASE: Base address of data memory region
//   Used by TEST_CASE_*_V* macros to load input data
// - VLENB_CACHE: Cache for VLENB value (length of V registers in bytes)
//   Used by TEST_CASE_CHECK_VLENB
// - HELPER_GPR: Scratch register
//   Used by TEST_CASE_CHECK_VLENB to calculate the required vector length
#ifndef SIG_BASE
# error "SIG_BASE is not specified"
#endif // SIG_BASE
#ifndef DATA_BASE
# error "DATA_BASE"
#endif // DATA_BASE
#ifndef VLENB_CACHE
# error "VLENB_CACHE is not defined"
#endif // VLENB_CACHE
#ifndef HELPER_GPR
# error "HELPER_GPR is not defined"
#endif // HELPER_GPR

// Bits mstatus[10:9] have the vector state
#define MSTATUS_VS_SHIFT 9

#define MSTATUS_VS_OFF     (0x0 << MSTATUS_VS_SHIFT)
#define MSTATUS_VS_INITIAL (0x1 << MSTATUS_VS_SHIFT)
#define MSTATUS_VS_CLEAN   (0x2 << MSTATUS_VS_SHIFT)
#define MSTATUS_VS_DIRTY   (0x3 << MSTATUS_VS_SHIFT)
#define MSTATUS_VS_MASK    (0x3 << MSTATUS_VS_SHIFT)

// RVTEST_V_ENABLE enables the vector unit
// Perform the following steps:
// - Set mstatus.vs to OFF
// - Set mstatus.vs to INITIAL
// - Read out vlenb and store in VLENB_CACHE
#define RVTEST_V_ENABLE()                                               \
    li HELPER_GPR, MSTATUS_VS_MASK ;                                    \
    csrrc zero, mstatus, HELPER_GPR ;                                   \
    li HELPER_GPR, MSTATUS_VS_INITIAL ;                                 \
    csrrs zero, mstatus, HELPER_GPR ;                                   \
    csrr VLENB_CACHE, vlenb ;

// VLE() exands to a vle${SEW}.v instruction
// E.g. VLEV(64) -> vle64.v
#define VLE(SEW) \
    vle ## SEW ##.v

// RVTEST_SIGUPD_V() stores the contests of a vector register in the signature
// AVL is the application vector length
// SEW defines the element size in bits (8, 16, 32, or 64)
// VREG is a VR that holds the data
// offset will be updated (to the next 8-byte boundary)
#define RVTEST_SIGUPD_V(AVL, SEW, VREG)                                 \
    CHK_OFFSET(SIG_BASE, REGWIDTH, 0) ;                                 \
    addi HELPER_GPR, SIG_BASE, offset ;                                 \
    vse ## SEW ##.v VREG, (HELPER_GPR) ;                                \
    .set offset, offset + (AVL * SEW / 8) ;                             \
    .if (offset & 7) > 0 ;                                              \
    .set offset, (offset + 8) & ~7 ;                                    \
    .endif ;

// Emit a run-time test for (VLENB<(AVL*SEW/8)) and jump to SKIP_LABEL if so
// This macro implicitly assumes that LMUL=1
#define TEST_CASE_CHECK_VLENB(AVL, SEW, SKIP_LABEL)                     \
    li HELPER_GPR, (AVL*SEW/8) ;                                        \
    blt VLENB_CACHE, HELPER_GPR, SKIP_LABEL ;

// TEST_CASE_<FORMAT> macros use the following convention:
// R..GPR
// F..FPR
// V..VR
// W..VR which is input and output
// U..unsigned immediate
// _M..enable masking (adding the ", v0.t" mnemonic operand)
// Order of operands matches the mnemonic (e.g. vd vs2 vs1)A
// Examples:
//   VV -> INST VD (out), VS2 (in)
//   VVVU -> INST VD (out), VS2 (in), VS1 (in), UIMM
//   WV -> INST VD (in/out), VS2 (in)

// TEST_CASE_VV() runs a single vector instruction test.
// The instruction has the following form:
//   VINST VD, VS2
// Steps are:
//   - Configures vector registers:
//     AVL (application vector length - number of elements) (0..31)
//     MA=1 (mask agnostic)
//     TA=1 (tail agnostic)
//     SEW (set element width) (8, 16, 32, 64)
//     LMUL=1 (vector register group multiplier)
//   - Load data from provided offset into VS2
//   - Perform VINST VD, VS2
//   - Append result into signature
#define TEST_CASE_VV(AVL, SEW, VINST, VD, VS2, DOFF2)                   \
    TEST_CASE_CHECK_VLENB(AVL, SEW, 1f) ;                               \
    vsetivli x0, AVL, e ## SEW, m1, ta, ma ;                            \
    addi HELPER_GPR, DATA_BASE, DOFF2 ;                                 \
    VLE(SEW) VS2, (HELPER_GPR) ;                                        \
    VINST VD, VS2 ;                                                     \
    RVTEST_SIGUPD_V(AVL, SEW, VD)                                       \
1:                                                                      \

// TEST_CASE_VV_M() runs a single masked vector instruction test.
// The instruction has the following form:
//   VINST VD, VS2, v0.t
// Steps are:
//   - Configures vector registers:
//     AVL (application vector length - number of elements) (0..31)
//     MA=1 (mask agnostic)
//     TA=1 (tail agnostic)
//     SEW (set element width) (8, 16, 32, 64)
//     LMUL=1 (vector register group multiplier)
//   - Load data from provided offset into VS2
//   - Clear VD
//   - Perform VINST VD, VS2, v0.t
//   - Append result into signature
#define TEST_CASE_VV_M(AVL, SEW, VINST, VD, VS2, DOFF2)                 \
    TEST_CASE_CHECK_VLENB(AVL, SEW, 1f) ;                               \
    vsetivli x0, AVL, e ## SEW, m1, ta, ma ;                            \
    addi HELPER_GPR, DATA_BASE, DOFF2 ;                                 \
    VLE(SEW) VS2, (HELPER_GPR) ;                                        \
    vxor.vv VD, VD, VD ;                                                \
    VINST VD, VS2, v0.t ;                                               \
    RVTEST_SIGUPD_V(AVL, SEW, VD)                                       \
1:                                                                      \

// TEST_CASE_WV() runs a single vector instruction test.
// The instruction has the following form:
//   VINST VD, VS2
// Steps are:
//   - Configures vector registers:
//     AVL (application vector length - number of elements) (0..31)
//     MA=1 (mask agnostic)
//     TA=1 (tail agnostic)
//     SEW (set element width) (8, 16, 32, 64)
//     LMUL=1 (vector register group multiplier)
//   - Load data from provided offset into VS2 and VD
//   - Perform VINST VD, VS2
//   - Append result into signature
#define TEST_CASE_WV(AVL, SEW, VINST, VD, DOFF, VS2, DOFF2)             \
    TEST_CASE_CHECK_VLENB(AVL, SEW, 1f) ;                               \
    vsetivli x0, AVL, e ## SEW, m1, ta, ma ;                            \
    addi HELPER_GPR, DATA_BASE, DOFF2 ;                                 \
    VLE(SEW) VS2, (HELPER_GPR) ;                                        \
    addi HELPER_GPR, DATA_BASE, DOFF ;                                  \
    VLE(SEW) VD, (HELPER_GPR) ;                                         \
    VINST VD, VS2 ;                                                     \
    RVTEST_SIGUPD_V(AVL, SEW, VD)                                       \
1:                                                                      \

// TEST_CASE_VVR() runs a single vector instruction test.
// The instruction has the following form:
//   VINST VD, VS2, RS1
// Steps are:
//   - Configures vector registers:
//     AVL (application vector length - number of elements) (0..31)
//     MA=1 (mask agnostic)
//     TA=1 (tail agnostic)
//     SEW (set element width) (8, 16, 32, 64)
//     LMUL=1 (vector register group multiplier)
//   - Load data from provided offset into VS2 and VS1
//   - Perform VINST VD, VS2, RS1, RM
//   - Append result into signature
#define TEST_CASE_VVR(AVL, SEW, VINST, VD, VS2, DOFF2, RS1, DOFF1)      \
    TEST_CASE_CHECK_VLENB(AVL, SEW, 1f) ;                               \
    vsetivli x0, AVL, e ## SEW, m1, ta, ma ;                            \
    addi HELPER_GPR, DATA_BASE, DOFF2 ;                                 \
    VLE(SEW) VS2, (HELPER_GPR) ;                                        \
    addi HELPER_GPR, DATA_BASE, DOFF1 ;                                 \
    LREG RS1, (HELPER_GPR) ;                                            \
    VINST VD, VS2, RS1 ;                                                \
    RVTEST_SIGUPD_V(AVL, SEW, VD)                                       \
1:                                                                      \

// TEST_CASE_VVR_M() runs a single masked vector instruction test.
// The instruction has the following form:
//   VINST VD, VS2, RS1, v0.t
// Steps are:
//   - Configures vector registers:
//     AVL (application vector length - number of elements) (0..31)
//     MA=1 (mask agnostic)
//     TA=1 (tail agnostic)
//     SEW (set element width) (8, 16, 32, 64)
//     LMUL=1 (vector register group multiplier)
//   - Load data from provided offset into VS2 and VS1
//   - Clear VD
//   - Perform VINST VD, VS2, RS1, RM
//   - Append result into signature
#define TEST_CASE_VVR_M(AVL, SEW, VINST, VD, VS2, DOFF2, RS1, DOFF1)    \
    TEST_CASE_CHECK_VLENB(AVL, SEW, 1f) ;                               \
    vsetivli x0, AVL, e ## SEW, m1, ta, ma ;                            \
    addi HELPER_GPR, DATA_BASE, DOFF2 ;                                 \
    VLE(SEW) VS2, (HELPER_GPR) ;                                        \
    addi HELPER_GPR, DATA_BASE, DOFF1 ;                                 \
    LREG RS1, (HELPER_GPR) ;                                            \
    vxor.vv VD, VD, VD ;                                                \
    VINST VD, VS2, RS1, v0.t ;                                          \
    RVTEST_SIGUPD_V(AVL, SEW, VD)                                       \
1:                                                                      \

// TEST_CASE_VVU() runs a single vector instruction test.
// The instruction has the following form:
//   VINST VD, VS2, UIMM
// Steps are:
//   - Configures vector registers:
//     AVL (application vector length - number of elements) (0..31)
//     MA=1 (mask agnostic)
//     TA=1 (tail agnostic)
//     SEW (set element width) (8, 16, 32, 64)
//     LMUL=1 (vector register group multiplier)
//   - Load data from provided offset into VS2
//   - Perform VINST VD, VS2, UIMM
//   - Append result into signature
#define TEST_CASE_VVU(AVL, SEW, VINST, VD, VS2, DOFF2, UIMM)            \
    TEST_CASE_CHECK_VLENB(AVL, SEW, 1f) ;                               \
    vsetivli x0, AVL, e ## SEW, m1, ta, ma ;                            \
    addi HELPER_GPR, DATA_BASE, DOFF2 ;                                 \
    VLE(SEW) VS2, (HELPER_GPR) ;                                        \
    VINST VD, VS2, UIMM ;                                               \
    RVTEST_SIGUPD_V(AVL, SEW, VD)                                       \
1:                                                                      \

// TEST_CASE_VVU_M() runs a single masked vector instruction test.
// The instruction has the following form:
//   VINST VD, VS2, UIMM, v0.t
// Steps are:
//   - Configures vector registers:
//     AVL (application vector length - number of elements) (0..31)
//     MA=1 (mask agnostic)
//     TA=1 (tail agnostic)
//     SEW (set element width) (8, 16, 32, 64)
//     LMUL=1 (vector register group multiplier)
//   - Load data from provided offset into VS2
//   - Clear VD
//   - Perform VINST VD, VS2, UIMM
//   - Append result into signature
#define TEST_CASE_VVU_M(AVL, SEW, VINST, VD, VS2, DOFF2, UIMM)          \
    TEST_CASE_CHECK_VLENB(AVL, SEW, 1f) ;                               \
    vsetivli x0, AVL, e ## SEW, m1, ta, ma ;                            \
    addi HELPER_GPR, DATA_BASE, DOFF2 ;                                 \
    VLE(SEW) VS2, (HELPER_GPR) ;                                        \
    vxor.vv VD, VD, VD ;                                                \
    VINST VD, VS2, UIMM, v0.t ;                                         \
    RVTEST_SIGUPD_V(AVL, SEW, VD)                                       \
1:                                                                      \

// TEST_CASE_WVU() runs a single vector instruction test.
// The instruction has the following form:
//   VINST VD, VS2, UIMM
// Steps are:
//   - Configures vector registers:
//     AVL (application vector length - number of elements) (0..31)
//     MA=1 (mask agnostic)
//     TA=1 (tail agnostic)
//     SEW (set element width) (8, 16, 32, 64)
//     LMUL=1 (vector register group multiplier)
//   - Load data from provided offset into VS2 and VD
//   - Perform VINST VD, VS2, UIMM
//   - Append result into signature
#define TEST_CASE_WVU(AVL, SEW, VINST, VD, DOFF, VS2, DOFF2, UIMM)      \
    TEST_CASE_CHECK_VLENB(AVL, SEW, 1f) ;                               \
    vsetivli x0, AVL, e ## SEW, m1, ta, ma ;                            \
    addi HELPER_GPR, DATA_BASE, DOFF2 ;                                 \
    VLE(SEW) VS2, (HELPER_GPR) ;                                        \
    addi HELPER_GPR, DATA_BASE, DOFF ;                                  \
    VLE(SEW) VD, (HELPER_GPR) ;                                         \
    VINST VD, VS2, UIMM ;                                               \
    RVTEST_SIGUPD_V(AVL, SEW, VD)                                       \
1:                                                                      \

// TEST_CASE_VVV() runs a single vector instruction test.
// The instruction has the following form:
//   VINST VD, VS2, VS1
// Steps are:
//   - Configures vector registers:
//     AVL (application vector length - number of elements) (0..31)
//     MA=1 (mask agnostic)
//     TA=1 (tail agnostic)
//     SEW (set element width) (8, 16, 32, 64)
//     LMUL=1 (vector register group multiplier)
//   - Load data from provided offset into VS2 and VS1
//   - Perform VINST VD, VS2, VS1
//   - Append result into signature
#define TEST_CASE_VVV(AVL, SEW, VINST, VD, VS2, DOFF2, VS1, DOFF1)      \
    TEST_CASE_CHECK_VLENB(AVL, SEW, 1f) ;                               \
    vsetivli x0, AVL, e ## SEW, m1, ta, ma ;                            \
    addi HELPER_GPR, DATA_BASE, DOFF2 ;                                 \
    VLE(SEW) VS2, (HELPER_GPR) ;                                        \
    addi HELPER_GPR, DATA_BASE, DOFF1 ;                                 \
    VLE(SEW) VS1, (HELPER_GPR) ;                                        \
    VINST VD, VS2, VS1 ;                                                \
    RVTEST_SIGUPD_V(AVL, SEW, VD)                                       \
1:                                                                      \

// TEST_CASE_VVV_M() runs a single masked vector instruction test.
// The instruction has the following form:
//   VINST VD, VS2, VS1, v0.t
// Steps are:
//   - Configures vector registers:
//     AVL (application vector length - number of elements) (0..31)
//     MA=1 (mask agnostic)
//     TA=1 (tail agnostic)
//     SEW (set element width) (8, 16, 32, 64)
//     LMUL=1 (vector register group multiplier)
//   - Load data from provided offset into VS2 and VS1
//   - Clear VD
//   - Perform VINST VD, VS2, VS1, RM
//   - Append result into signature
#define TEST_CASE_VVV_M(AVL, SEW, VINST, VD, VS2, DOFF2, VS1, DOFF1)    \
    TEST_CASE_CHECK_VLENB(AVL, SEW, 1f) ;                               \
    vsetivli x0, AVL, e ## SEW, m1, ta, ma ;                            \
    addi HELPER_GPR, DATA_BASE, DOFF2 ;                                 \
    VLE(SEW) VS2, (HELPER_GPR) ;                                        \
    addi HELPER_GPR, DATA_BASE, DOFF1 ;                                 \
    VLE(SEW) VS1, (HELPER_GPR) ;                                        \
    vxor.vv VD, VD, VD ;                                                \
    VINST VD, VS2, VS1, v0.t ;                                          \
    RVTEST_SIGUPD_V(AVL, SEW, VD)                                       \
1:                                                                      \

// TEST_CASE_WVV() runs a single vector instruction test.
// The instruction has the following form:
//   VINST VD, VS2, VS1
// Steps are:
//   - Configures vector registers:
//     AVL (application vector length - number of elements) (0..31)
//     MA=1 (mask agnostic)
//     TA=1 (tail agnostic)
//     SEW (set element width) (8, 16, 32, 64)
//     LMUL=1 (vector register group multiplier)
//   - Load data from provided offset into VS2, VS1, and VD
//   - Perform VINST VD, VS2, VS1
//   - Append result into signature
#define TEST_CASE_WVV(AVL, SEW, VINST, VD, DOFF, VS2, DOFF2, VS1, DOFF1) \
    TEST_CASE_CHECK_VLENB(AVL, SEW, 1f) ;                               \
    vsetivli x0, AVL, e ## SEW, m1, ta, ma ;                            \
    addi HELPER_GPR, DATA_BASE, DOFF2 ;                                 \
    VLE(SEW) VS2, (HELPER_GPR) ;                                        \
    addi HELPER_GPR, DATA_BASE, DOFF1 ;                                 \
    VLE(SEW) VS1, (HELPER_GPR) ;                                        \
    addi HELPER_GPR, DATA_BASE, DOFF ;                                  \
    VLE(SEW) VD, (HELPER_GPR) ;                                         \
    VINST VD, VS2, VS1 ;                                                \
    RVTEST_SIGUPD_V(AVL, SEW, VD)                                       \
1:                                                                      \

// TEST_CASE_BLOCK_64B_* macros contain 64 byte blocks of test data
// This is sufficent for:
// - 64 x  8 bits
// - 32 x 16 bits
// - 16 x 32 bits
// -  8 x 64 bits

#define TEST_CASE_BLOCK_64B_0                                           \
    .dword 0x0f1e2d3c4b5a6978 ;                                         \
    .dword 0xf0e1d2c3b4a59687 ;                                         \
    .dword 0x5a5a5a5a5a5a5a5a ;                                         \
    .dword 0xa5a5a5a5a5a5a5a5 ;                                         \
    .dword 0x1011121314151617 ;                                         \
    .dword 0xf8f9fafbfcfdfeff ;                                         \
    .dword 0x0111213141516171 ;                                         \
    .dword 0x8f9fafbfcfdfefff ;

#define TEST_CASE_BLOCK_64B_1                                           \
    .dword 0x00ff00ff00ff00ff ;                                         \
    .dword 0xff00ff00ff00ff00 ;                                         \
    .dword 0x0880088008800880 ;                                         \
    .dword 0x8008800880088008 ;                                         \
    .dword 0x0001020304050607 ;                                         \
    .dword 0x08090a0b0c0d0e0f ;                                         \
    .dword 0x8081828384858687 ;                                         \
    .dword 0x88898a8b8c8d8e8f ;

#define TEST_CASE_BLOCK_64B_2                                           \
    .dword 0x0000000000000000 ;                                         \
    .dword 0x0000000000000000 ;                                         \
    .dword 0x0000000000000000 ;                                         \
    .dword 0x0000000000000000 ;                                         \
    .dword 0x0000000000000000 ;                                         \
    .dword 0x0000000000000000 ;                                         \
    .dword 0x0000000000000000 ;                                         \
    .dword 0x0000000000000000 ;

#define TEST_CASE_BLOCK_64B_3                                           \
    .dword 0xffffffffffffffff ;                                         \
    .dword 0xffffffffffffffff ;                                         \
    .dword 0xffffffffffffffff ;                                         \
    .dword 0xffffffffffffffff ;                                         \
    .dword 0xffffffffffffffff ;                                         \
    .dword 0xffffffffffffffff ;                                         \
    .dword 0xffffffffffffffff ;                                         \
    .dword 0xffffffffffffffff ;

// TEST_CASE_BLOCK_256B_* macros contain 256 byte blocks of test data
// This is sufficent for:
// - 256 x  8 bits
// - 128 x 16 bits
// -  64 x 32 bits
// -  32 x 64 bits

#define TEST_CASE_BLOCK_256B_0 \
TEST_CASE_BLOCK_64B_0 \
TEST_CASE_BLOCK_64B_1 \
TEST_CASE_BLOCK_64B_2 \
TEST_CASE_BLOCK_64B_3

#endif // RISCV_TEST_SUITE_TEST_MACROS_VECTOR_H
