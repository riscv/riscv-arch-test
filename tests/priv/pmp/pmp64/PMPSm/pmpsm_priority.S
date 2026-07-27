// --------------------------------------------------------------------------------
// Copyright (C) 2025 Harvey Mudd College & Oklahoma State University, UET Lahore, Habib University
// SPDX-License-Identifier: Apache-2.0
//
// Title           : Comprehensive PMP (Physical Memory Protection) Verification
// Authors         : Umer Shahid, Allen Baum, David Harris
//                  Muhammad Abdullah, Hamza Ali, Muhammad Zain
//
// Description : This test verifies the functionality and enforcement of
//               Physical Memory Protection (PMP) configurations in RISC-V
//               systems. It specifically tests the Read, Write, and Execute
//               permissions for a designated memory region, ensuring that
//               the PMP settings are correctly applied and that the system
//               behaves as expected when accessing this region.
//
// Coverpoints :  cp_priority for PMPM is fully covered in this file.
//
// Test Cases  :  Testing that first matching region has priority to determine
//                XWR. Set up 7 overlapping NAPOT regions all based at REGIONSTART
//                with sizes NAPOT_REGION_SIZE, 2x, 4x, 8x, 16x, 32x, 64x. Region 0
//                is smallest and highest priority. Cycle through the 6 legal XWR
//                values across regions 0-5; region 6 has no permissions. Make
//                {lw, sw, jalr} to the last word of each region. Access fault if
//                the matching region prohibits access.

// --------------------------------------------------------------------------------


##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['Sm']
# params:
#   MXLEN: 64
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv64i_zicsr_zifencei
##### END_TEST_CONFIG #####

// Define the size of the signature region
#define SIGUPD_COUNT 200


// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

#if UDB_PMP_GRANULARITY > 3
  #define NAPOT_REGION_SIZE     (1 << (UDB_PMP_GRANULARITY))
  #define NAPOT_PRIORITY_ALIGN  (UDB_PMP_GRANULARITY + 6)
#else
  #define NAPOT_REGION_SIZE     (1 << (UDB_PMP_GRANULARITY + 1))
  #define NAPOT_PRIORITY_ALIGN  (UDB_PMP_GRANULARITY + 7)
#endif

.macro VERIFICATION_RWX ADDRESS TEST_CASE

    // Execution Access Check
    LA (a4, \ADDRESS)
    LA(x1, 1f)                          // Store the return Address in x1
    RVTEST_FENCEI                              // sync I-cache: a prior store may have updated this executable region
    \TEST_CASE\()_3:
    jalr ra, 0(a4)
    nop
    nop
1:
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)


   LI(a4, NOP)                                              // Value to write (NOP)
    // Store Access Check
    LA(a5, \ADDRESS)                                      // Address to be verified

    \TEST_CASE\()_1:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)

    LA(a5, \ADDRESS)                                      // Address to be verified

    \TEST_CASE\()_2:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)                 // Signature update

.endm

main:
    // Loop to SET ALL pmpcfg REGs to zero
    .set pmpcfgi, CSR_PMPCFG0
    .rept UDB_NUM_PMP_ENTRIES/8
    csrw pmpcfgi , x0
    .set pmpcfgi, pmpcfgi+2
    .endr

    // Loop to SET ALL pmpaddr REGs to zero
    .set pmpaddri, CSR_PMPADDR0
    .rept UDB_NUM_PMP_ENTRIES
    csrw pmpaddri, x0
    .set pmpaddri, pmpaddri+1
    .endr

#define PMPREGION_LXWR_1000 ((((PMP_L|                  PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT))
#define PMPREGION_LXWR_1101 ((((PMP_L|      PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LXWR_1011 ((((PMP_L|PMP_R|PMP_W|      PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT))
#define PMPREGION_LXWR_1100 ((((PMP_L|            PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT))
#define PMPREGION_LXWR_1001 ((((PMP_L|PMP_R            |PMP_NAPOT)&0xFF) << PMP4_CFG_SHIFT))
#define PMPREGION_LXWR_1111 ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP5_CFG_SHIFT))
#define PMPREGION_LXWR_1000_6 ((((PMP_L|                PMP_NAPOT)&0xFF) << PMP6_CFG_SHIFT))

    RVTEST_PMP_SET_BACKGROUND x4

    // Set 7 overlapping NAPOT regions all based at TEST_FOR_EXECUTION, with
    // sizes NAPOT_REGION_SIZE, 2x, 4x, 8x, 16x, 32x, 64x.
    // pmpaddr[i] = (REGIONSTART >> 2) | ((1<<i) * NAPOT_REGION_SIZE/8 - 1)
    LA(x5, TEST_FOR_EXECUTION)
    srl x5, x5, PMP_SHIFT
    .set i, 0
    .set pmpaddri, CSR_PMPADDR0
    .rept 7
    LI(x6, (1 << i) * (NAPOT_REGION_SIZE / 8) - 1)
    or x6, x5, x6
    csrw pmpaddri, x6
    .set i, i+1
    .set pmpaddri, pmpaddri+1
    .endr

    // Set NAPOT cfg for all 7 regions in pmpcfg0
    LI(x4, (PMPREGION_LXWR_1000_6|PMPREGION_LXWR_1111|PMPREGION_LXWR_1001|PMPREGION_LXWR_1100|PMPREGION_LXWR_1011|PMPREGION_LXWR_1101|PMPREGION_LXWR_1000))
    csrw pmpcfg0, x4

//                                            Verification Section
// Test Case: 1 : Accessing at end of region 0 (size 1x) with No Permissions

    VERIFICATION_RWX   (TEST_FOR_EXECUTION + 1*NAPOT_REGION_SIZE - 4), test_1

// Test Case: 2 : Accessing at end of region 1 (size 2x) with XR Permissions

    VERIFICATION_RWX   (TEST_FOR_EXECUTION + 2*NAPOT_REGION_SIZE - 4), test_2

// Test Case: 3 : Accessing at end of region 2 (size 4x) with WR Permissions

    VERIFICATION_RWX   (TEST_FOR_EXECUTION + 4*NAPOT_REGION_SIZE - 4), test_3

// Test Case: 4 : Accessing at end of region 3 (size 8x) with X Permissions

    VERIFICATION_RWX   (TEST_FOR_EXECUTION + 8*NAPOT_REGION_SIZE - 4), test_4

// Test Case: 5 : Accessing at end of region 4 (size 16x) with R Permissions

    VERIFICATION_RWX   (TEST_FOR_EXECUTION + 16*NAPOT_REGION_SIZE - 4), test_5

// Test Case: 6 : Accessing at end of region 5 (size 32x) with XWR Permissions

    VERIFICATION_RWX   (TEST_FOR_EXECUTION + 32*NAPOT_REGION_SIZE - 4), test_6

// Test Case: 7 : Accessing at end of region 6 (size 64x) with No Permissions

    VERIFICATION_RWX   (TEST_FOR_EXECUTION + 64*NAPOT_REGION_SIZE - 4), test_7
RVTEST_CODE_END

RVTEST_DATA_BEGIN
.p2align 4

// Test case strings for reporting
test_1_str: .string "\"test: 1; cp: pmpm_priority_sw\""
test_2_str: .string "\"test: 2; cp: pmpm_priority_lw\""
test_3_str: .string "\"test: 3; cp: pmpm_priority_jalr\""

.p2align 12
TEST_FOR_EXECUTION_0:
    jr ra                                                        // return pad before the aligned NAPOT priority region

.p2align NAPOT_PRIORITY_ALIGN
TEST_FOR_EXECUTION:
    .rept (16*NAPOT_REGION_SIZE)                                // 64*NAPOT_REGION_SIZE bytes: covers the largest overlapping region
    nop
    .endr

RETURN_INSTRUCTION:
    nop
    nop
    jr ra                                                        // Get back to the point from where TEST_FOR_EXECUTION was called.

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
