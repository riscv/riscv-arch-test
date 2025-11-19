// Copyright (c) 2023. RISC-V International. All rights reserved.
// SPDX-License-Identifier: BSD-3-Clause
// -----------
// This file contains test macros for vector tests

#ifndef RISCV_TEST_SUITE_TEST_MACROS_VECTOR_H
#define RISCV_TEST_SUITE_TEST_MACROS_VECTOR_H

#include "model_test.h"
#include "riscv_arch_test.h"

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


/************************************* RVTEST_SIG_SETUP ************************************/
/**** RVTEST_SIG_SETUP creates signature region to support self-checking tests          ****/
/**** - Main signature region for results from test, initialized with correct values    ****/
/****   for self-checking                                                               ****/
/**** - Trap handler signature region                                                   ****/
/*******************************************************************************************/
.macro RVTEST_SIG_SETUP_V
  .align 4
  .global begin_signature
  begin_signature:
  .global rvtest_sig_begin
  rvtest_sig_begin:

    // Create canary at beginning of signature region to detect overwrites
    sig_begin_canary:
      CANARY

    // Main signature region
    .align 3
    signature_base:
      #ifdef SELFCHECK
        // Preload signature region with correct values for self-checking
        #include SIGNATURE_FILE
      #else
        // Initialize signature region to known value for initial pass
        .fill SIGUPD_COUNT*(XLEN/32),4,0xdeadbeef
      #endif

    // Signature region for trap handlers
    #ifdef rvtest_mtrap_routine
      tsig_begin_canary:
        CANARY
      mtrap_sigptr:
        .fill 64*(XLEN/32),4,0xdeadbeef
      tsig_end_canary:
        CANARY
    #endif

    // Create canary at end of signature region to detect overwrites
    sig_end_canary:
      CANARY

  .align 4
  .global rvtest_sig_end
  rvtest_sig_end:
  .global end_signature
  end_signature:
.endm
/*********************************** end of RVTEST_SIG_SETUP *********************************/


#endif // RISCV_TEST_SUITE_TEST_MACROS_VECTOR_H
