// ---------------------------------------------------------------------------
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
//
// Coverpoints : cp_misaligned_off for PMPZca is partially covered
//               in this test file.
//
// Test Cases  : Check that misaligned 32-bit fetches that cross a OFF PMP boundary fail.
//               Setting up 3 standard consecutive OFF PMP regions with L=1, XWR=111
//               (XWR = 000 for region 3).Place an uncompressed ret = jalr straddling the
//               start and end of the second regions. Attempt jalr to each ret.
//
// ---------------------------------------------------------------------------
##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: ['I','Zca']
# params:
#   MXLEN: 32
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv32i_zca_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpzca_misaligned_off.S"
#define SIGUPD_COUNT 50

// Enable trap handler
#define rvtest_mtrap_routine
#define RVTEST_PRIV_TEST

#define SKIP_MEPC

// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

#define REGION_SIZE         (1<<(RVMODEL_PMP_GRAIN+2))

.macro VERIFICATION_RWX ADDRESS, TEST_CASE
    \TEST_CASE\()_1:
    LA(x15, \ADDRESS)               // Address to be verified
    c.jalr x15
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)
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
#define PMP0CFG             ((((PMP_L|PMP_R|PMP_W|PMP_X         )&0xFF) << PMP0_CFG_SHIFT))
#define PMP1CFG             ((((PMP_L|PMP_R|PMP_W|PMP_X         )&0xFF) << PMP1_CFG_SHIFT))
#define PMP2CFG             ((((PMP_L|PMP_R|PMP_W|PMP_X         )&0xFF) << PMP2_CFG_SHIFT))
#define PMPADDRESS_TOP_GLOBAL       -1                                              // All memory region

#define REGIONSTART         TEST_FOR_EXECUTION_1  // RAM_BASE_ADDR + PROGRAM_SIZE

    LA(x4, PMPADDRESS_TOP_GLOBAL)
    csrw    pmpaddr15, x4

    //Lock the Background region.
    LI(x4, PMP_REGION_GLOBAL)
    csrw pmpcfg3, x4

//                                          Verification Section
// Test Case: Setting up 3 OFF regions with LWXR = 1111

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT  // This will create dynamic PMP_ADDRESS_0
    csrw pmpaddr0, x5

    LA(x4, PMP0CFG)
    csrw pmpcfg0, x4

    LA(x5, REGIONSTART)
    addi x5, x5, REGION_SIZE
    srl  x5, x5, PMP_SHIFT  // This will create dynamic PMP_ADDRESS_1
    csrw pmpaddr1, x5

    LA(x4, PMP1CFG)
    csrw pmpcfg0, x4

    LA(x5, REGIONSTART)
    addi x5, x5, 2*REGION_SIZE
    srl x5, x5, PMP_SHIFT  // This will create dynamic PMP_ADDRESS_2
    csrw pmpaddr2, x5

    LA(x4, PMP2CFG)
    csrw pmpcfg0, x4

    // Test Case 1: Uncompressed return straddling the start of 2nd region
    VERIFICATION_RWX TEST_FOR_EXECUTION_2, test_1

    // Test Case 2: Uncompressed return straddling the end of 2nd region
    VERIFICATION_RWX TEST_FOR_EXECUTION_4, test_2

    j exit                                                      // Verification Complete, exit the test

.align 13
TEST_FOR_EXECUTION_1:
    .rept (((1<<(RVMODEL_PMP_GRAIN+2)) / 2) -1)
    nop
    .endr

TEST_FOR_EXECUTION_2:
    jalr x0, x1, 0                                              //uncompressed return straddling the start of the second region

TEST_FOR_EXECUTION_3:
    .rept (((1<<(RVMODEL_PMP_GRAIN+2)) / 2) -2)
    nop
    .endr

TEST_FOR_EXECUTION_4:
    jalr x0, x1, 0                                              // Uncompressed return straddling the end of the second region

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
test_1_str: .string "\"test: 1; cp: pmpzca_aligned_na4_region_execute\""

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
