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
// Coverpoints : cp_cret_napot for PMPZca is fully covered in this test file.
//
// Test Cases  : Check that 16-bit fetches adjacent to a NAPOT PMP boundary succeed.
//               Set up a standard NAPOT PMP region with L=1, XWR = 111. Place four
//               c.ret = c.jr ra statements just below, at bottom, at top, and just
//               above PMP region, half of which are on 16-bit boundaries.
//               Attempt jalr to each c.ret.
// ---------------------------------------------------------------------------
##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['Zca','Sm']
# params:
#   MXLEN: 64
#   NUM_PMP_ENTRIES: '>0'
#   PMP_NAPOT_SUPPORTED: true
# MARCH: rv64i_zca_zicsr_zifencei
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpzca_cret_napot.S"
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

#define PMP0CFG             ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT))

#define REGIONSTART         TEST_FOR_EXECUTION_1
#if UDB_PMP_GRANULARITY != 2
    #define PMP_MASK            ~((1 << (UDB_PMP_GRANULARITY - 3))-1)
    #define PMP_REGION_SIZE     (1 << (UDB_PMP_GRANULARITY - 3)) - 1
    #define SIZE (1<<(UDB_PMP_GRANULARITY)
#else
    #define PMP_MASK            ~0
    #define PMP_REGION_SIZE     0
    #define SIZE (1<<(UDB_PMP_GRANULARITY+1)
#endif

    RVTEST_PMP_SET_BACKGROUND x4

//                                          Verification Section
// Test Case: NAPOT Region with L->1 and XWR->111

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    LI(x6, PMP_MASK)
    and x5, x5, x6
    LI(x6, PMP_REGION_SIZE)
    or x5, x5, x6
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

.p2align 10
.skip (0x806)                                                  // shifted +4B so REGIONSTART lands at PMP_NAPOT_REGION_START, not PMP_REGION_START
TEST_FOR_EXECUTION_0:
    ret                                                         // Compressed return just before the start of region

TEST_FOR_EXECUTION_1:
    ret                                                         // Compressed return inside the region
    .rept ((SIZE) -4 ) /2)                     // (size of region - size of 2 returns) / size of nop
    nop
    .endr

TEST_FOR_EXECUTION_2:
    ret                                                         // Compressed return at the top of the region

TEST_FOR_EXECUTION_3:
    ret                                                         // Compressed return just above the region
    nop

RETURN_INSTRUCTION:
    nop
    nop
    jr ra                                                       // Get back to the point from where TEST_FOR_EXECUTION was called.


RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
