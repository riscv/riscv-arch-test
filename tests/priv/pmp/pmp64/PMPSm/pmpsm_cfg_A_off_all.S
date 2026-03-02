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
// Coverpoints : cp_cfg_A_off_all for PMPM is fully covered in this test file.
//
// Test Cases  : Checking that A=OFF never matches for each region. For each
//               standard region with pmpcfg.L=1, pmpcfg.A=OFF, pmpcfg.XWR=000.
//               Fetching, reading and writing from that region. Should succeed
//               because region is off even though inaccessible.
// --------------------------------------------------------------------------------
##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['I','Smpmp']
# params:
#   MXLEN: 64
# MARCH: rv64i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpsm_cfg_A_off_all.S"
#define SIGUPD_COUNT 50

// Enable trap handler
#define rvtest_mtrap_routine
#define RVTEST_PRIV_TEST

#define SKIP_MEPC

// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

.macro VERIFICATION_RWX ADDRESS, TEST_CASE
    // Execution Access Check
    LA (a4, \ADDRESS)
    LI(x4, 0xACCE)                        // Store a value which is to be checked in trap handler
    LA(x4, 1f)                            // Store the return Address in x1
    \TEST_CASE\()_3:
    jalr ra, 0(a4)
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)               // Signature update for jalr
    nop
    nop
1:
    nop
    nop

    // Store Access Check
    LA(a5, \ADDRESS)                                         // Address to be verified
    LI(a4, DOUBLE_NOP)                                              // Value to write (DOUBLE_NOP)
    \TEST_CASE\()_2:
    sw a4, 0(a5)                                             // Word store test
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)               // Signature update for sw
    nop
    nop

    // Load Access Check
    \TEST_CASE\()_1:
    lw a4, 0(a5)                                             // Word load test
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)               // Signature update for lw
    nop
    nop

.endm

main:
    // Loop to SET ALL pmpcfg REGs to zero
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
    csrw pmpcfgi , x0
    .set pmpcfgi, pmpcfgi+2
    .endr

    // Loop to SET ALL pmpaddr REGs to zero
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
    csrw pmpaddri, x0
    .set pmpaddri, pmpaddri+1
    .endr


#define PMP_REGION_GLOBAL    ((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF)      // Background region with RWX enable.
#define REGIONSTART            0x80002000        // RAM_BASE_ADDR + PROGRAM_SIZE
#define PMP_MASK            ~(1 << (RVMODEL_PMP_GRAIN - 1))
#define PMP_REGION_SIZE     (1 << (RVMODEL_PMP_GRAIN - 1)) - 1

#if RVMODEL_PMP_GRAIN != 0
  #define STANDARD_REGION   (((REGIONSTART >> PMP_SHIFT) & PMP_MASK) | PMP_REGION_SIZE)
#else
  #define STANDARD_REGION   (REGIONSTART >> PMP_SHIFT)
#endif


    LA(x4, -1)
    csrw     pmpaddr15, x4

    //Lock the Background region.
    LI(x4, (PMP_REGION_GLOBAL << PMP7_CFG_SHIFT))
    csrw pmpcfg2, x4

//                                            Verification Section
// Test Case: 1 -- No Permissions given to the PMP Region 14

    LI(x5, STANDARD_REGION)
    csrw pmpaddr14, x5

    LI(x4, (0x80 << PMP6_CFG_SHIFT))
    csrw pmpcfg2, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_1

    RVTEST_GOTO_MMODE

// Test Case: 2 -- No Permissions given to the PMP Region 13

    LI(x5, STANDARD_REGION)
    csrw pmpaddr13, x5

    LI(x4, (0x80 << PMP5_CFG_SHIFT))
    csrw pmpcfg2, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_2

    RVTEST_GOTO_MMODE

// Test Case: 3 -- No Permissions given to the PMP Region 12

    LI(x5, STANDARD_REGION)
    csrw pmpaddr12, x5

    LI(x4, (0x80 << PMP4_CFG_SHIFT))
    csrw pmpcfg2, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_3

    RVTEST_GOTO_MMODE

// Test Case: 4 -- No Permissions given to the PMP Region 11

    LI(x5, STANDARD_REGION)
    csrw pmpaddr11, x5

    LI(x4, (0x80 << PMP3_CFG_SHIFT))
    csrw pmpcfg2, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_4

    RVTEST_GOTO_MMODE

// Test Case: 5 -- No Permissions given to the PMP Region 10

    LI(x5, STANDARD_REGION)
    csrw pmpaddr10, x5

    LI(x4, (0x80 << PMP2_CFG_SHIFT))
    csrw pmpcfg2, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_5

    RVTEST_GOTO_MMODE

// Test Case: 6 -- No Permissions given to the PMP Region 9

    LI(x5, STANDARD_REGION)
    csrw pmpaddr9, x5

    LI(x4, (0x80 << PMP1_CFG_SHIFT))
    csrw pmpcfg2, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_6

    RVTEST_GOTO_MMODE

// Test Case: 7 -- No Permissions given to the PMP Region 8

    LI(x5, STANDARD_REGION)
    csrw pmpaddr8, x5

    LI(x4, (0x80 << PMP0_CFG_SHIFT))
    csrw pmpcfg2, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_7

    RVTEST_GOTO_MMODE

// Test Case: 8 -- No Permissions given to the PMP Region 7

    LI(x5, STANDARD_REGION)
    csrw pmpaddr7, x5

    LI(x4, (0x80 << PMP7_CFG_SHIFT))
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_8

    RVTEST_GOTO_MMODE

// Test Case: 9 -- No Permissions given to the PMP Region 6

    LI(x5, STANDARD_REGION)
    csrw pmpaddr6, x5

    LI(x4, (0x80 << PMP6_CFG_SHIFT))
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_9

    RVTEST_GOTO_MMODE

// Test Case: 10 -- No Permissions given to the PMP Region 5

    LI(x5, STANDARD_REGION)
    csrw pmpaddr5, x5

    LI(x4, (0x80 << PMP5_CFG_SHIFT))
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_10

    RVTEST_GOTO_MMODE

// Test Case: 11 -- No Permissions given to the PMP Region 4

    LI(x5, STANDARD_REGION)
    csrw pmpaddr4, x5

    LI(x4, (0x80 << PMP4_CFG_SHIFT))
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_11

    RVTEST_GOTO_MMODE

// Test Case: 12 -- No Permissions given to the PMP Region 3

    LI(x5, STANDARD_REGION)
    csrw pmpaddr3, x5

    LI(x4, (0x80 << PMP3_CFG_SHIFT))
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_12

    RVTEST_GOTO_MMODE

// Test Case: 13 -- No Permissions given to the PMP Region 2

    LI(x5, STANDARD_REGION)
    csrw pmpaddr2, x5

    LI(x4, (0x80 << PMP2_CFG_SHIFT))
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_13

    RVTEST_GOTO_MMODE

// Test Case: 14 -- No Permissions given to the PMP Region 1

    LI(x5, STANDARD_REGION)
    csrw pmpaddr1, x5

    LI(x4, (0x80 << PMP1_CFG_SHIFT))
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_14

    RVTEST_GOTO_MMODE

// Test Case: 15 -- No Permissions given to the PMP Region 0

    LI(x5, STANDARD_REGION)
    csrw pmpaddr0, x5

    LI(x4, (0x80 << PMP0_CFG_SHIFT))
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_15

    RVTEST_GOTO_MMODE

// Test Case: 16 -- No Permissions given to the PMP Region 0

    LI(x5, STANDARD_REGION)
    csrw pmpaddr0, x5

    LI(x4, (0x80 << PMP0_CFG_SHIFT))
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_16

    j exit                                                        // Verification Complete, exit the test

.align 12
.align (RVMODEL_PMP_GRAIN+2)
TEST_FOR_EXECUTION:
    .rept (1<<(RVMODEL_PMP_GRAIN+2))
    nop
    .endr

RETURN_INSTRUCTION:
    nop
    nop
    jr ra                                                        // Get back to the point from where TEST_FOR_EXECUTION was called.

exit:

RVTEST_CODE_END
RVTEST_DATA_BEGIN
.align 4

// Test case strings for reporting
canary_mismatch: .string "Testcase signature canary mismatch!"
test_1_str: .string "\"test: 1; cp: cp_cfg_A_off_all_lw\""
test_2_str: .string "\"test: 2; cp: cp_cfg_A_off_all_sw\""
test_3_str: .string "\"test: 3; cp: cp_cfg_A_off_all_x\""

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
