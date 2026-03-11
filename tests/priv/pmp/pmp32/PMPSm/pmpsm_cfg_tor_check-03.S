// --------------------------------------------------------------------------------
// Copyright (C) 2025 Harvey Mudd College & Oklahoma State University, UET Lahore, Habib University
// SPDX-License-Identifier: Apache-2.0
//
// Title        : Comprehensive PMP (Physical Memory Protection) Verification
// Authors      : Umer Shahid, Allen Baum, David Harris
//                Muhammad Abdullah, Hamza Ali, Muhammad Zain
//
// Description : This test verifies the functionality and enforcement of
//               Physical Memory Protection (PMP) configurations in RISC-V
//               systems. It specifically tests the Read, Write, and Execute
//               permissions for a designated memory region, ensuring that
//               the PMP settings are correctly applied and that the system
//               behaves as expected when accessing this region.
//
// Coverpoints  : 3rd test case of cp_cfg_A_tor_non-overlap for PMPM is covered
//                in this test file.
//
// Test case    : We check that there is no match when pmpaddr0 >= pmpaddr1 with
//                the following cfgs pmpcfg1.L=1, pmpcfg1.A=TOR, pmpcfg1.XWR=000,
//                pmpcfg0.L=0, pmpcfg0.A=OFF, pmpcfg1.XWR=000. This test exercises
//                test case 3 that is when pmpaddr0 =  all 1s

// --------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['I']
# params:
#   MXLEN: 32
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv32i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpsm_cfg_tor_check-03.S"
#define SIGUPD_COUNT 50

// Enable trap handler
#define rvtest_mtrap_routine
#define RVTEST_PRIV_TEST

#define SKIP_MEPC

// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

#define g       (1<<(RVMODEL_PMP_GRAIN+2))

.macro VERIFICATION_RWX ADDRESS TEST_CASE

    LI(a4, NOP)                                             // Value to write (NOP)

    LA(a5, (\ADDRESS-4))                                    // Address to be verified
    \TEST_CASE\()_1:
    sw a4, 0(a5)                                            // word-level store test
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)                               // Signature update

    LA(a5, (\ADDRESS))                                      // Address to be verified
    \TEST_CASE\()_2:
    sw a4, 0(a5)                                            // word-level store test
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)                                   // Signature update

    LA(a5, (\ADDRESS+4))                                    // Address to be verified
    \TEST_CASE\()_3:
    sw a4, 0(a5)                                            // word-level store test
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)                                   // Signature update

    LA(a5, (\ADDRESS-4))                                    // Address to be verified
    \TEST_CASE\()_4:
    lw a4, 0(a5)                                            // Word load test
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_4, test_4_str)                               // Signature update

    LA(a5, (\ADDRESS))                                      // Address to be verified
    \TEST_CASE\()_5:
    lw a4, 0(a5)                                            // Word load test
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_5, test_5_str)                                   // Signature update

    LA(a5, (\ADDRESS+4))                                    // Address to be verified
    \TEST_CASE\()_6:
    lw a4, 0(a5)                                            // Word load test
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_6, test_6_str)                                    // Signature update

    LA (a4, (\ADDRESS-4))
    LI(x4, 0xACCE)                                            // Store a value which is to be checked in trap handler
    LA(x1, 1f)                                                // Store the return Address in x1
    jalr ra, 0(a4)
    nop
    nop
1:
    nop
    nop

    LA (a4, (\ADDRESS))
    LA(x1, 2f)                                                // Store the return Address in x1
    jalr ra, 0(a4)
    nop
    nop
2:
    nop
    nop

    LA (a4, (\ADDRESS+4))
    LA(x1, 3f)                                                // Store the return Address in x1
    jalr ra, 0(a4)
    nop
    nop
3:
    nop
    nop

.endm

main:
    // Loop to SET ALL pmpcfg REGs to zeros
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/4
    csrw pmpcfgi , x0
    .set pmpcfgi, pmpcfgi+1
    .endr

    // Loop to SET ALL pmpaddr REGs to zero
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
    csrw pmpaddri, x0
    .set pmpaddri, pmpaddri+1
    .endr

#define PMP_REGION_GLOBAL          ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT))  // Background region with RWX enable.
#define PMPREGION_UPPER_BOUND      ((((PMP_L                  |PMP_TOR)  &0xFF) << PMP1_CFG_SHIFT))

#define PMPADDRESS_TOP_GLOBAL       -1                                              // All memory region


    LA(x4, PMPADDRESS_TOP_GLOBAL)
    csrw    pmpaddr15, x4

    //Lock the Background region.
    LI(x4, PMP_REGION_GLOBAL)
    csrw pmpcfg3, x4

    //addresses for a default TOR region
    LA(x4, TEST_FOR_EXECUTION)
    addi    x5, x4, g
    srl x4, x4, PMP_SHIFT
    srl x5, x5, PMP_SHIFT

//                                          Verification Section

// Test Case:  pmpaddr0 = all1s

    li x5, -1
    csrw    pmpaddr0, x5
    csrw    pmpaddr1, x4

    LI(x4, PMPREGION_UPPER_BOUND)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION,test_1

    RVTEST_GOTO_MMODE

    j exit                                                      // Verification Complete, exit the test

.align 13
.align (RVMODEL_PMP_GRAIN+2)
TEST_FOR_EXECUTION:
    .rept (1<<(RVMODEL_PMP_GRAIN+2))
    nop
    .endr

RETURN_INSTRUCTION:
    nop
    nop
    jr ra                                                       // Get back to the point from where TEST_FOR_EXECUTION was called.

exit:

RVTEST_CODE_END

RVTEST_DATA_BEGIN
.align 4

// Test case strings for reporting
canary_mismatch: .string "Testcase signature canary mismatch!"
test_1_str: .string "\"test: 1; cp: pmpm_cfg_tor_check3_store_access_at_pmpaddr-4\""
test_2_str: .string "\"test: 2; cp: pmpm_cfg_tor_check3_store_access_at_pmpaddr\""
test_3_str: .string "\"test: 3; cp: pmpm_cfg_tor_check3_store_access_at_pmpaddr+4\""
test_4_str: .string "\"test: 4; cp: pmpm_cfg_tor_check3_load_access_at_pmpaddr-4\""
test_5_str: .string "\"test: 5; cp: pmpm_cfg_tor_check3_load_access_at_pmpaddr\""
test_6_str: .string "\"test: 6; cp: pmpm_cfg_tor_check3_load_access_at_pmpaddr+4\""


RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
