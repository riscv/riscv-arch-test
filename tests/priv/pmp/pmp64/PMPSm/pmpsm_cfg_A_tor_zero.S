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
//               systems. It checks that region 0 extends from 0 to pmpaddr0
//               in TOR mode.
//
// Coverpoints:  cp_cfg_A_tor0 for PMPM is fully covered in this test file.
//
// Test Cases  : Checking region 0 extends from 0 to pmpaddr0 in TOR mode.
//                 Dropping the background region. With pmpcfg0.L=1, pmpcfg0.A=TOR,
//                 pmpcfg0.XWR=111, default TOR region: {lw, sw, jalr} to {0,
//                 pmpaddr0-4, pmpaddr0}.
// --------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['Sm']
# params:
#   MXLEN: 64
#   NUM_PMP_ENTRIES: '>0'
#   PMP_TOR_SUPPORTED: true
# MARCH: rv64i_zicsr_zifencei
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpsm_cfg_A_tor_zero.S"
#define SIGUPD_COUNT 50



#define SKIP_MTVAL

// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

.macro VERIFICATION_RWX ADDRESS, TEST_CASE

    LI(a4, DOUBLE_NOP)                                              // Value to write (DOUBLE_NOP)

    LA(a5, (\ADDRESS))                                         // Address to be verified
    \TEST_CASE\()_1:
    sw a4, 0(a5)                                             // word-level store test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4,\TEST_CASE\()_1,test_1_str)               // Signature update

    LA(a5, (\ADDRESS-4))                                     // Address to be verified
    \TEST_CASE\()_2:
    sw a4, 0(a5)                                             // word-level store test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4,\TEST_CASE\()_2,test_2_str)               // Signature update

    LI(a4, 0x00008067)                                       // ret (jalr x0, 0(ra)): on cores where addr 0 is mapped RAM the store lands and the later execute probe at 0 must return
    LI(a5, 0)
    LA(x1, 4f)                                               // Address to be verified
    sw a4, 0(a5)                                             // word-level store test
    nop
4:
    nop


    LA(a5, (\ADDRESS))                                         // Address to be verified
    \TEST_CASE\()_3:
    lw a4, 0(a5)                                             // Word load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4,\TEST_CASE\()_3,test_3_str)               // Signature update

    LA(a5, (\ADDRESS-4))                                         // Address to be verified
    \TEST_CASE\()_4:
    lw a4, 0(a5)                                             // Word load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4,\TEST_CASE\()_4,test_4_str)               // Signature update

    LA(x1, 5f)
    LI(a5, 0)                                                   // Address to be verified
    lw a4, 0(a5)                                             // word-level store test
    nop

5:
    nop


    LA (a4, (\ADDRESS))
    LA(x1, 1f)                                                // Store the return Address in x1
    RVTEST_FENCEI                              // sync I-cache: a prior store may have updated this executable region
    jalr ra, 0(a4)
    nop
1:
    nop

    LA (a4, (\ADDRESS-4))
    LA(x1, 2f)                            // Store the return Address in x1
    jalr ra, 0(a4)
    nop
2:
    nop

    LI(a5, 0)
    LA(x1, 3f)                            // Store the return Address in x1
    jalr ra, 0(a5)
    nop
3:
    nop

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

#define PMPREGION_TOR                 ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_TOR)&0xFF)   << PMP0_CFG_SHIFT))


    RVTEST_PMP_SET_BACKGROUND x4

    LA(x4, TEST_FOR_EXECUTION)
    srl x4, x4, PMP_SHIFT
    csrw     pmpaddr0, x4

//                                            Verification Section
// Test Case 1: Default TOR region with XWR permissions

    LI(x4, PMPREGION_TOR)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_1

    RVTEST_GOTO_MMODE

RVTEST_CODE_END
RVTEST_DATA_BEGIN
.p2align 4

// Test case strings for reporting
test_1_str: .string "\"test: 1; cp: pmpm_cfg_A_tor_zero_store_access_at_pmpaddr0\""
test_2_str: .string "\"test: 2; cp: pmpm_cfg_A_tor_zero_store_access_at_pmpaddr0-4\""
test_3_str: .string "\"test: 3; cp: pmpm_cfg_A_tor_zero_load_access_at_pmpaddr0\""
test_4_str: .string "\"test: 4; cp: pmpm_cfg_A_tor_zero_load_access_at_pmpaddr0-4\""


.p2align 12
.p2align (UDB_PMP_GRANULARITY)
TEST_FOR_EXECUTION_0:
    .rept (1 << (UDB_PMP_GRANULARITY - 2))              // one PMP granule of return-instruction fillers: places the region on the next granule boundary (= PMP_REGION_START at coverage grain 2), grain-aligned at larger grains
    jr ra
    .endr

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
