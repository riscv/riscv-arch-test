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
// Coverpoints :  cp_priority for PMPM is fully covered in this file.
//
// Test Cases  :  Testing that first matching region has priority to determining
//                XWR. Set up 7 even/odd pairs of TOR regions, where each pair
//                starts (even) at the standard location and has pair i has size
//                i*g (in odd reg) so the regions partially overlap. Set the even
//                pmpcfg to 0 (OFF). Set the odd pmpcfg to TOR and cycle through
//                the 6 legal XWR values for each pair. Make {lw, sw, jalr} to
//                each of (PMP_writable_regs-1) addresses at end of each region.
//                Access fault if the relevant (highest priority) region prohibits
//                access.
//
// --------------------------------------------------------------------------------

#define SKIP_MEPC
##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: ['I','Smpmp']
# params:
#   MXLEN: 32
# MARCH: rv32i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpsm_priority.S"
#define SIGUPD_COUNT 50

// Enable trap handler
#define rvtest_mtrap_routine
#define RVTEST_PRIV_TEST

// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

#define g   (1 << (RVMODEL_PMP_GRAIN + 2))

.macro VERIFICATION_RWX ADDRESS TEST_CASE

    LI(x4, 0xACCE)                      // Store a value which is to be checked in trap handler
    // Execution Access Check
    LA (a4, \ADDRESS)
    LA(x1, 1f)                          // Store the return Address in x1
    jalr ra, 0(a4)
    nop
    nop
1:
    nop
    nop

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

#define PMP_REGION_GLOBAL   ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT))  // Background region with RWX enable.
#define PMPREGION_LXWR_1000 ((((PMP_L|                  PMP_TOR  )&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LXWR_1101 ((((PMP_L|      PMP_R|PMP_X|PMP_TOR  )&0xFF) << PMP3_CFG_SHIFT))
#define PMPREGION_LXWR_1011 ((((PMP_L|PMP_R|PMP_W|      PMP_TOR  )&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LXWR_1100 ((((PMP_L|            PMP_X|PMP_TOR  )&0xFF) << PMP3_CFG_SHIFT))
#define PMPREGION_LXWR_1001 ((((PMP_L|PMP_R            |PMP_TOR  )&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LXWR_1111 ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_TOR  )&0xFF) << PMP3_CFG_SHIFT))


    LA(x4, -1)                      // All memory region
    csrw    pmpaddr15, x4

    //Lock the Background region.
    LI(x4, PMP_REGION_GLOBAL)
    csrw pmpcfg3, x4

    LA(x4, TEST_FOR_EXECUTION)
    srl x4, x4, PMP_SHIFT
    addi x5, x0, g

    // REGIONSTART in even PMPADDR
    .set pmpaddri, CSR_PMPADDR0
    .rept 7
    csrw pmpaddri, x4
    .set pmpaddri, pmpaddri+2
    .endr

    // REGIONSTART + i*g in odd PMPADDR
    LA(x5, TEST_FOR_EXECUTION)
    .set pmpaddri, CSR_PMPADDR0+1
    .rept 7
    addi x5, x5, g
    srl x6, x5, PMP_SHIFT
    csrw pmpaddri, x6
    .set pmpaddri, pmpaddri+2
    .endr

    // Setting the even pmpcfg to 0 and odd pmpcfg to TOR & and rotating through the 6 legal XWR values.
    LI(x4, (PMPREGION_LXWR_1101|PMPREGION_LXWR_1000))
    csrw pmpcfg0, x4
    LI(x5, (PMPREGION_LXWR_1100|PMPREGION_LXWR_1011))
    csrw pmpcfg1, x5
    LI(x4, (PMPREGION_LXWR_1111|PMPREGION_LXWR_1001))
    csrw pmpcfg2, x4
    LI(x5, PMPREGION_LXWR_1000)
    csrw pmpcfg3, x5

//                                          Verification Section
// Test Case: 1 : Accessing at end of region with No Permissions

    VERIFICATION_RWX   (TEST_FOR_EXECUTION + g - 4), test_1

// Test Case: 2 : Accessing at end of region with XR Permissions

    VERIFICATION_RWX   (TEST_FOR_EXECUTION + 2*g - 4), test_2

// Test Case: 3 : Accessing at end of region with WR Permissions

    VERIFICATION_RWX   (TEST_FOR_EXECUTION + 3*g - 4), test_3

// Test Case: 4 : Accessing at end of region with X Permissions

    VERIFICATION_RWX   (TEST_FOR_EXECUTION + 4*g - 4), test_4

// Test Case: 5 : Accessing at end of region with R Permissions

    VERIFICATION_RWX   (TEST_FOR_EXECUTION + 5*g - 4), test_5

// Test Case: 6 : Accessing at end of region with XWR Permissions

    VERIFICATION_RWX   (TEST_FOR_EXECUTION + 6*g - 4), test_6

// Test Case: 6 : Accessing at end of region with No Permissions

    VERIFICATION_RWX   (TEST_FOR_EXECUTION + 7*g - 4), test_7

    j exit                                                      // Verification Complete, exit the test

.align 13
.align (RVMODEL_PMP_GRAIN+2)
TEST_FOR_EXECUTION:     // Largest Region of size 7*g
    .rept 7*(1<<(RVMODEL_PMP_GRAIN+2))
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
test_1_str: .string "\"test: 1; cp: pmpm_priority_sw\""
test_2_str: .string "\"test: 2; cp: pmpm_priority_lw\""

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
