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
// Coverpoints : cp_cfg_X0_all, cp_cfg_X1_all, cp_cfg_RW00_all, cp_cfg_RW10_all
//                 and cp_cfg_RW11_all for PMPM is partially covered in this file.
//
// Test Cases  : Rolling legal XWR starting from region with lowest priority i.e.,
//               region 14 to region with highest priority i.e., region 0 such
//               that each of the writable registers gets each of the 6 legal
//               combinations at least once.
// --------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['Sm']
# params:
#   MXLEN: 64
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv64i_zicsr_zifencei
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpsm_cfg_XWR_all-01.S"
#define SIGUPD_COUNT 200




// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN


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

#define PMPREGION_XWR_000   ((PMP_L|                  PMP_NAPOT)&0xFF)
#define PMPREGION_XWR_100   ((PMP_L|            PMP_X|PMP_NAPOT)&0xFF)
#define PMPREGION_XWR_001   ((PMP_L|PMP_R|            PMP_NAPOT)&0xFF)
#define PMPREGION_XWR_101   ((PMP_L|PMP_R|      PMP_X|PMP_NAPOT)&0xFF)
#define PMPREGION_XWR_011   ((PMP_L|PMP_R|PMP_W      |PMP_NAPOT)&0xFF)
#define PMPREGION_XWR_111   ((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF)


#define PMPADDRESS            TEST_FOR_EXECUTION                              // Test section address
#if UDB_PMP_GRANULARITY != 2
    #define PMP_MASK            ~((1 << (UDB_PMP_GRANULARITY - 3))-1)
    #define PMP_REGION_SIZE     (1 << (UDB_PMP_GRANULARITY - 3)) - 1
#else
    #define PMP_MASK            ~0
    #define PMP_REGION_SIZE     0
#endif

    RVTEST_PMP_SET_BACKGROUND x4

    LA(x4, PMPADDRESS)
    srl x4, x4, PMP_SHIFT

.if UDB_PMP_GRANULARITY != 2
    LI(t0, PMP_MASK)
    and x4, x4, t0
    LI(t0, PMP_REGION_SIZE)
    or x4, x4, t0
.endif

    .set pmpaddri, CSR_PMPADDR0
    .rept UDB_NUM_PMP_ENTRIES
    csrw pmpaddri, x4
    .set pmpaddri, pmpaddri+1
    .endr

//                                            Verification Section
// Test Case: 1 -- No Permissions given to the PMP Region 14

    LI(x4, (PMPREGION_XWR_000 << PMP6_CFG_SHIFT))
    csrw pmpcfg2, x4

    PMP_VERIFICATION_RWX_ALL    TEST_FOR_EXECUTION , test_1

    RVTEST_GOTO_MMODE

// Test Case: 2 -- X Permissions given to the PMP Region 13

    LI(x4, (PMPREGION_XWR_100 << PMP5_CFG_SHIFT))
    csrw pmpcfg2, x4

    PMP_VERIFICATION_RWX_ALL    TEST_FOR_EXECUTION , test_2

    RVTEST_GOTO_MMODE

// Test Case: 3 -- R Permissions given to the PMP Region 12

    LI(x4, (PMPREGION_XWR_001 << PMP4_CFG_SHIFT))
    csrw pmpcfg2, x4

    PMP_VERIFICATION_RWX_ALL    TEST_FOR_EXECUTION , test_3

    RVTEST_GOTO_MMODE

// Test Case: 4 -- XR Permissions given to the PMP Region 11

    LI(x4, (PMPREGION_XWR_101 << PMP3_CFG_SHIFT))
    csrw pmpcfg2, x4

    PMP_VERIFICATION_RWX_ALL    TEST_FOR_EXECUTION , test_4

    RVTEST_GOTO_MMODE

// Test Case: 5 -- WR Permissions given to the PMP Region 10

    LI(x4, (PMPREGION_XWR_011 << PMP2_CFG_SHIFT))
    csrw pmpcfg2, x4

    PMP_VERIFICATION_RWX_ALL    TEST_FOR_EXECUTION , test_5

    RVTEST_GOTO_MMODE

// Test Case: 6 -- XWR Permissions given to the PMP Region 9

    LI(x4, (PMPREGION_XWR_111 << PMP1_CFG_SHIFT))
    csrw pmpcfg2, x4

    PMP_VERIFICATION_RWX_ALL    TEST_FOR_EXECUTION , test_6

    RVTEST_GOTO_MMODE

// Test Case: 7 -- No Permissions given to the PMP Region 8

    LI(x4, (PMPREGION_XWR_000 << PMP0_CFG_SHIFT))
    csrw pmpcfg2, x4

    PMP_VERIFICATION_RWX_ALL    TEST_FOR_EXECUTION , test_7

    RVTEST_GOTO_MMODE

// Test Case: 8 -- X Permissions given to the PMP Region 7

    LI(x4, (PMPREGION_XWR_100 << PMP7_CFG_SHIFT))
    csrw pmpcfg0, x4

    PMP_VERIFICATION_RWX_ALL    TEST_FOR_EXECUTION , test_8

    RVTEST_GOTO_MMODE

RVTEST_CODE_END

RVTEST_DATA_BEGIN

// Test case strings for reporting
test_1_str: .string "\"test: 1; cp: pmpm_cfg_XWR_all_sb\""
test_2_str: .string "\"test: 2; cp: pmpm_cfg_XWR_all_sh\""
test_3_str: .string "\"test: 3; cp: pmpm_cfg_XWR_all_sw\""
test_4_str: .string "\"test: 4; cp: pmpm_cfg_XWR_all_sd\""
test_5_str: .string "\"test: 5; cp: pmpm_cfg_XWR_all_lb\""
test_6_str: .string "\"test: 6; cp: pmpm_cfg_XWR_all_lbu\""
test_7_str: .string "\"test: 7; cp: pmpm_cfg_XWR_all_lh\""
test_8_str: .string "\"test: 8; cp: pmpm_cfg_XWR_all_lhu\""
test_9_str: .string "\"test: 9; cp: pmpm_cfg_XWR_all_lw\""
test_10_str: .string "\"test: 10; cp: pmpm_cfg_XWR_all_lwu\""
test_11_str: .string "\"test: 11; cp: pmpm_cfg_XWR_all_ld\""
test_12_str: .string "\"test: 12; cp: pmpm_cfg_XWR_all_jalr\""

.p2align 12
.p2align (UDB_PMP_GRANULARITY)
TEST_FOR_EXECUTION_0:
    .rept PMP_NAPOT_REGION_PAD_WORDS   // g_napot-byte pad -> NAPOT region-under-test at 0x80005008 (PMP_NAPOT_REGION_START); pmpaddr matches STANDARD_REGION, region does not cover the pad
    jr ra
    .endr

.p2align (UDB_PMP_GRANULARITY)
TEST_FOR_EXECUTION:
    .rept (1<<(UDB_PMP_GRANULARITY))
    nop
    .endr

RETURN_INSTRUCTION:
    nop
    nop
    jr ra                                                        // Get back to the point from where TEST_FOR_EXECUTION was called.

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
