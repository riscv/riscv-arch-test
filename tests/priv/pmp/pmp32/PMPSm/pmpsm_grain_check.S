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
// Coverpoints: cp_grain_check for PMPM is fully covered in this test file.
//
// Test case  : Checking that granularity matches expectations. We write 0
//              to pmpcfg0, all 1s to pmpaddr0, and then read back pmpaddr0.
//              Index of least-significant bit set should be G.
// --------------------------------------------------------------------------------

#define SKIP_MEPC
##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['I']
# params:
#   MXLEN: 32
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv32i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpsm_grain_check.S"
#define SIGUPD_COUNT 50

// Enable trap handler
#define rvtest_mtrap_routine
#define RVTEST_PRIV_TEST

// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

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

#define PMPADDRESS_TOP_GLOBAL       -1                                              // All memory region
#define REGIONSTART         TEST_FOR_EXECUTION      // RAM_BASE_ADDR + PROGRAM_SIZE

    LA(x4, PMPADDRESS_TOP_GLOBAL)
    csrw    pmpaddr15, x4

    //Lock the Background region.
    LI(x4, PMP_REGION_GLOBAL)
    csrw pmpcfg3, x4

    LA(x4, TEST_FOR_EXECUTION)
    srl x4, x4, PMP_SHIFT
    csrw    pmpaddr0, x4

//                                          Verification Section
// Test Case: Write 0 to pmpcfg0, all 1s to pmpaddr0, read back pmpaddr0.

    li x6, 0
    csrw pmpcfg0, x6
    li x6, -1
    test_1:
         # Write x6 to pmpaddr0, read back and check against expected.
         RVTEST_SIGUPD_CSR_WRITE(pmpaddr0, x6, test_1, test_1_str)

    test_2:
        # Read pmpaddr0 into x7 and check against expected.
        RVTEST_SIGUPD_CSR_READ(pmpaddr0, x7, test_2, test_2_str)


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
test_1_str: .string "\"test: 1; cp: cp_pmp_grain_check_1\""
test_2_str: .string "\"test: 1; cp: cp_pmp_grain_check_2\""

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
