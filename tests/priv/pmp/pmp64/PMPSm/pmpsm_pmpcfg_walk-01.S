// --------------------------------------------------------------------------------
// Copyright (C) 2025 Harvey Mudd College & Oklahoma State University, UET Lahore, Habib University
// Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
// SPDX-License-Identifier: Apache-2.0
//
// Title           : PMP configuration CSR walk verification
// Authors         : Umer Shahid, Allen Baum, David Harris
//                  Muhammad Abdullah, Hamza Ali, Muhammad Zain
//                  Jordan Carlin
//
// Description : This test verifies WARL-safe writes to PMP configuration CSRs.
//               It writes zero to implemented pmpcfg CSRs and checks the
//               readback signature.
//
// Coverpoints : cp_pmpcfg_walk for PMPSm is fully covered in
//               this test file.
//
// Test Cases  : Write zero to pmpcfg CSRs and check readback.
// --------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['Sm']
# params:
#   MXLEN: 64
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv64i_zicsr_zifencei
##### END_TEST_CONFIG #####

// Define the size of the signature region
#define SIGUPD_COUNT 8

// Enable trap handler
#define RVTEST_PRIV_TEST

// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

main:

    // -----------------------------------------------------------------------
    // SET even pmpcfg CSRs to zero
    // -----------------------------------------------------------------------
    .set pmpcfgi, CSR_PMPCFG0
    .rept UDB_NUM_PMP_ENTRIES/8
1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, x0, 1b, test_0_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    RVTEST_GOTO_MMODE

RVTEST_CODE_END
RVTEST_DATA_BEGIN

// Test case strings for reporting
test_0_str: .string "\"write zero to even pmpcfg CSRs; cp: cp_pmpcfg_walk\""

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
