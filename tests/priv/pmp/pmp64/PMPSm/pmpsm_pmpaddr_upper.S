// --------------------------------------------------------------------------------
// Copyright (C) 2025 Harvey Mudd College & Oklahoma State University, UET Lahore, Habib University
// Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
// SPDX-License-Identifier: Apache-2.0
//
// Title           : PMP address upper-bits verification
// Authors         : Umer Shahid, Allen Baum, David Harris
//                  Muhammad Abdullah, Hamza Ali, Muhammad Zain
//                  Jordan Carlin
//
// Description : This test verifies the architecturally fixed upper bits of RV64
//               pmpaddr CSRs. It writes ones to implemented pmpaddr CSRs and
//               checks bits 63:54 read back as zero.
//
// Coverpoints : cp_pmpaddr_upper_zero for PMPSm is fully covered in
//               this test file.
//
// Test Cases  : Write ones to pmpaddr CSRs and check bits 63:54 read back as zero.
// --------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['Sm']
# params:
#   MXLEN: 64
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv64i_zicsr_zifencei
##### END_TEST_CONFIG #####

// Define the size of the signature region
#define SIGUPD_COUNT 64

// Enable trap handler
#define RVTEST_PRIV_TEST

// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

main:
    RVTEST_GOTO_MMODE

    // -----------------------------------------------------------------------
    // Verify upper 10 pmpaddr bits remain zero after writing ones
    // -----------------------------------------------------------------------
    LI(t0, -1)
    LI(t1, 0xFFC0000000000000)
    .set pmpaddri, CSR_PMPADDR0
    .rept UDB_NUM_PMP_ENTRIES
1:  csrw pmpaddri, t0
    csrr t2, pmpaddri
    and t2, t2, t1
    RVTEST_SIGUPD(x2, x5, x4, t2, 1b, test_0_str)
    .set pmpaddri, pmpaddri+1
    .endr

    RVTEST_GOTO_MMODE

RVTEST_CODE_END
RVTEST_DATA_BEGIN

// Test case strings for reporting
test_0_str: .string "\"write ones to pmpaddr CSRs and check bits 63:54 are zero; cp: cp_pmpaddr_upper_zero\""

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
