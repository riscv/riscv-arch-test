// --------------------------------------------------------------------------------
// Copyright (C) 2025 Harvey Mudd College & Oklahoma State University, UET Lahore, Habib University
// Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
// SPDX-License-Identifier: Apache-2.0
//
// Title           : PMP address grain discovery verification
// Authors         : Umer Shahid, Allen Baum, David Harris
//                  Muhammad Abdullah, Hamza Ali, Muhammad Zain
//                  Jordan Carlin
//
// Description : This test verifies PMP address grain discovery.
//               It writes ones to pmpaddr0 with pmpcfg0 set to OFF and
//               checks the low bits needed to identify the grain.
//
// Coverpoints: cp_grain_check for PMPSm is fully covered in this test file.
//
// Test case  : Checking that granularity matches expectations. We write 0
//                to pmpcfg0, all 1s to pmpaddr0, and then read back pmpaddr0.
//                Index of least-significant bit set should be G.
//
// --------------------------------------------------------------------------------


##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['Sm']
# params:
#   MXLEN: 64
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv64i_zicsr_zifencei
##### END_TEST_CONFIG #####

// Define the size of the signature region
#define SIGUPD_COUNT 1


// Include framework macros
#include "riscv_arch_test.h"

#define PMP_GRAIN_CHECK_MASK ((1 << (UDB_PMP_GRANULARITY - 1)) - 1)

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



#define REGIONSTART            TEST_FOR_EXECUTION        // RAM_BASE_ADDR + PROGRAM_SIZE

    RVTEST_PMP_SET_BACKGROUND x4

    LA(x4, REGIONSTART)
    srl x4, x4, PMP_SHIFT
    csrw pmpaddr0, x4

//                                            Verification Section
// Test Case: Write 0 to pmpcfg0, all 1s to pmpaddr0, read back pmpaddr0.

    LI(x6, 0)
    csrw pmpcfg0, x6
    LI(x6, -1)
    csrw pmpaddr0, x6
    LI(t3, PMP_GRAIN_CHECK_MASK)
    test_0:
        csrr x7, pmpaddr0
        and x7, x7, t3
        RVTEST_SIGUPD(x2, x5, x4, x7, test_0, test_0_str)

    RVTEST_GOTO_MMODE

RVTEST_CODE_END
RVTEST_DATA_BEGIN

// Test case strings for reporting
test_0_str: .string "\"write ones to pmpaddr0 and check grain low bits; cp: cp_grain_check\""


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
