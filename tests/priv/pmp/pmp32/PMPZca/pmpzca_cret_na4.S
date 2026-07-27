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
// Coverpoints : cp_cret_na4 for PMPZca is fully covered in this test file.
//
// Test Cases  : Checking that 16-bit fetches adjacent to a NA4 PMP boundary succeed.
//               Set up a standard NA4 PMP region with L=1, XWR = 111. Placing four
//               c.ret = c.jr ra statements just below, at bottom, at top, and just
//               above PMP region, half of which are on 16-bit boundaries.
//               Attempt jalr to each c.ret.
//
// ---------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: ['I','Zca','Sm']
# params:
#   MXLEN: 32
#   NUM_PMP_ENTRIES: '>0'
#   PMP_NA4_SUPPORTED: true
# MARCH: rv32i_zca_zicsr_zifencei
##### END_TEST_CONFIG #####

// Define the size of the signature region
#define SIGUPD_COUNT 50




// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN


main:
    // Loop to SET ALL pmpcfg REGs to zero
    .set pmpcfgi, CSR_PMPCFG0
    .rept UDB_NUM_PMP_ENTRIES/4
    csrw pmpcfgi , x0
    .set pmpcfgi, pmpcfgi+1
    .endr

    // Loop to SET ALL pmpaddr REGs to zero
    .set pmpaddri, CSR_PMPADDR0
    .rept UDB_NUM_PMP_ENTRIES
    csrw pmpaddri, x0
    .set pmpaddri, pmpaddri+1
    .endr

#define PMP0CFG                 ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NA4  ) &0xFF)   << PMP0_CFG_SHIFT))

#define REGIONSTART             TEST_FOR_EXECUTION_1


    RVTEST_PMP_SET_BACKGROUND x4

//                                          Verification Section
// Test Case: NA4 Region with L->1 and XWR->111

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    csrw pmpaddr0, x5

    LA(x4, PMP0CFG)
    csrw pmpcfg0, x4

    //Test case1
    PMP_VERIFICATION_X_C TEST_FOR_EXECUTION_0, test1

    //Test case2
    PMP_VERIFICATION_X_C TEST_FOR_EXECUTION_1, test2

    //Test case3
    PMP_VERIFICATION_X_C TEST_FOR_EXECUTION_2, test3

    //Test case4
    PMP_VERIFICATION_X_C TEST_FOR_EXECUTION_3, test4

    j exit                                                      // Verification Complete, exit the test
exit:

RVTEST_CODE_END
RVTEST_DATA_BEGIN

// Test case strings for reporting
test_1_str: .string "\"test: 1; cp: pmpzca_cret_napot_execute\""

.p2align 11
.skip (0x802)
TEST_FOR_EXECUTION_0:
    ret                                                         // Compressed return just before the start of region

TEST_FOR_EXECUTION_1:
    ret                                                         // Compressed at the start of the region

TEST_FOR_EXECUTION_2:
    ret                                                         // Compressed return at the top of the region

TEST_FOR_EXECUTION_3:
    ret                                                         // Compressed return just above the region

RETURN_INSTRUCTION:
    nop
    nop
    jr ra                                                       // Get back to the point from where TEST_FOR_EXECUTION was called.

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
