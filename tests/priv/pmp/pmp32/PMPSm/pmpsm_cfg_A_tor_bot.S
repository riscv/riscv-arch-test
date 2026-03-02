// --------------------------------------------------------------------------------
// Copyright (C) 2025 Harvey Mudd College & Oklahoma State University, UET Lahore, Habib University
// SPDX-License-Identifier: Apache-2.0
//
// Title        : Comprehensive PMP (Physical Memory Protection) Verification
// Authors      : Umer Shahid, Allen Baum, David Harris
//                Muhammad Abdullah, Hamza Ali, Muhammad Zain
//
// Description  :This test verifies the functionality and enforcement of
//               Physical Memory Protection (PMP) configurations in RISC-V
//               systems. It specifically tests the Read, Write, and Execute
//               permissions for a designated memory region, ensuring that
//               the PMP settings are correctly applied and that the system
//               behaves as expected when accessing this region
//
// Coverpoints : cp_cfg_A_tor_bot for PMPM is fully covered in this test file.
//
// Test cases  : In this test, we check that region 1 extends from pmpaddr0 to
//              pmpaddr1. We set up a default TOR region, then make accesses
//              {lw,sw,jalr} at addresses {pmpadr0-4, pmpadr0, pmpadr1-4, pmpadr1}.
//
//              Test case 1: pmpcfg1.L=1, pmpcfg1.A = TOR, pmpcfg1.XWR=101,
//               pmpcfg0.L = 0, pmpcfg0.A = OFF, pmpcfg0.XWR = 000
//
//              Test case 2: pmpcfg1.L=1, pmpcfg1.A = TOR, pmpcfg1.XWR=101,
//               pmpcfg0.L = 1, pmpcfg0.A = OFF, pmpcfg0.XWR = 000
// --------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: ['I','Smpmp']
# params:
#   MXLEN: 32
# MARCH: rv32i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpsm_cfg_A_tor_bot.S"
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

.macro VERIFICATION_RWX ADDRESS, TEST_CASE

    LI(a4, NOP)                                             // Value to write (NOP)

    LA(a5, (\ADDRESS-4))                                    // Address to be verified
    \TEST_CASE\()_1:
    sw a4, 0(a5)                                            // word-level store test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)

    LA(a5, (\ADDRESS))                                      // Address to be verified
    \TEST_CASE\()_2:
    sw a4, 0(a5)                                            // word-level store test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)

    LA(a5, ((\ADDRESS+g)-4))                                // Address to be verified
    \TEST_CASE\()_3:
    sw a4, 0(a5)                                            // word-level store test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)

    LA(a5, (\ADDRESS+g))                                    // Address to be verified
    \TEST_CASE\()_4:
    sw a4, 0(a5)                                            // word-level store test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_4, test_4_str)

    LA(a5, (\ADDRESS-4))                                    // Address to be verified
    \TEST_CASE\()_5:
    lw a4, 0(a5)                                            // Word load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_5, test_5_str)

    LA(a5, (\ADDRESS))                                      // Address to be verified
    \TEST_CASE\()_6:
    lw a4, 0(a5)                                            // Word load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_6, test_6_str)

    LA(a5, ((\ADDRESS+g)-4))                                    // Address to be verified
    \TEST_CASE\()_7:
    lw a4, 0(a5)                                            // Word load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_7, test_7_str)

    LA(a5, (\ADDRESS+g))                                    // Address to be verified
    \TEST_CASE\()_8:
    lw a4, 0(a5)                                            // Word load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_8, test_8_str)

    LA (a4, (\ADDRESS-4))
    LI(x4, 0xACCE)                                            // Store a value which is to be checked in trap handler
    LA(x1, 1f)                                                // Store the return Address in x1
    jalr ra, 0(a4)
    nop
1:
    nop

    LA (a4, (\ADDRESS))
    LA(x1, 2f)                            // Store the return Address in x1
    jalr ra, 0(a4)
    nop
2:
    nop

    LA (a4, ((\ADDRESS+g)-4))
    LA(x1, 3f)                            // Store the return Address in x1
    jalr ra, 0(a4)
    nop
3:
    nop

    LA (a4, (\ADDRESS+g))
    LA(x1, 4f)                            // Store the return Address in x1
    jalr ra, 0(a4)
    nop
4:
    nop

.endm

main:
    // Loop to SET ALL pmpcfg REGs to zero
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


#define PMP_REGION_GLOBAL           ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT))  // Background region with RWX enable.
#define PMPREGION_UPPER_BOUND       ((((PMP_L|PMP_R      |PMP_X|PMP_TOR)  &0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LOWER_BOUND       ((((PMP_L)                            &0xFF) << PMP0_CFG_SHIFT))

    LA(x4, -1)                  // All memory region
    csrw    pmpaddr15, x4

    //Lock the Background region.
    LI(x4, PMP_REGION_GLOBAL)
    csrw pmpcfg3, x4

    LA(x4, TEST_FOR_EXECUTION)
    addi    x5, x4, g
    srl x4, x4, PMP_SHIFT
    srl x5, x5, PMP_SHIFT

    csrw    pmpaddr0, x4
    csrw    pmpaddr1, x5

//                                          Verification Section
// Test Case: 1

    LI(x4, PMPREGION_UPPER_BOUND)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_1

// Test Case: 2

    LI(x4, PMPREGION_UPPER_BOUND)
    csrw pmpcfg0, x4
    LI(x4, PMPREGION_LOWER_BOUND)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_2

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
test_1_str: .string "\"test: 1; cp: pmpm_cfg_A_tor_bot_store_access_at_pmpaddr0-4\""
test_2_str: .string "\"test: 2; cp: pmpm_cfg_A_tor_bot_store_access_at_pmpaddr0+4\""
test_3_str: .string "\"test: 3; cp: pmpm_cfg_A_tor_bot_store_access_at_pmpaddr1-4\""
test_4_str: .string "\"test: 4; cp: pmpm_cfg_A_tor_bot_store_access_at_pmpaddr1+4\""
test_5_str: .string "\"test: 5; cp: pmpm_cfg_A_tor_bot_load_access_at_pmpaddr0-4\""
test_6_str: .string "\"test: 6; cp: pmpm_cfg_A_tor_bot_load_access_at_pmpaddr0+4\""
test_7_str: .string "\"test: 7; cp: pmpm_cfg_A_tor_bot_load_access_at_pmpaddr1-4\""
test_8_str: .string "\"test: 8; cp: pmpm_cfg_A_tor_bot_load_access_at_pmpaddr1+4\""

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
