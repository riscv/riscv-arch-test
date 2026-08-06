// --------------------------------------------------------------------------------
// Copyright (C) 2025 Harvey Mudd College & Oklahoma State University, UET Lahore, Habib University
// Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
// SPDX-License-Identifier: Apache-2.0
//
// Title        : PMP configuration CSR walk verification
// Authors      : Umer Shahid, Allen Baum, David Harris
//                Muhammad Abdullah, Hamza Ali, Muhammad Zain
//                Jordan Carlin
//
// Description : This test verifies WARL-safe writes to PMP configuration CSRs.
//               It writes walking-one values to implemented pmpcfg CSRs and
//               checks the readback signature.
//
// Coverpoints : cp_pmpcfg_walk for PMPSm is partially in
//               this test file.
//
// Test Cases  : Write walking-one values to pmpcfg CSRs and check readback.
// --------------------------------------------------------------------------------
##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['Sm']
# params:
#   MXLEN: 32
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv32i_zicsr_zifencei
##### END_TEST_CONFIG #####
// Define the size of the signature region
#define SIGUPD_COUNT 48

// Enable trap handler
#define RVTEST_PRIV_TEST

// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

main:
    RVTEST_GOTO_MMODE

    // Count of even pmpcfg registers:
    //   16 PMPs → 2 even regs (pmpcfg0, pmpcfg2)
    //   64 PMPs → 8 even regs (pmpcfg0 .. pmpcfg14, step 2)
    // -----------------------------------------------------------------------

    // --- pmpcfg even walking ones, bit 10 ---
    .set pmpcfgi, CSR_PMPCFG0
    .rept UDB_NUM_PMP_ENTRIES/8
1:  LI(t2, 1 << 10)
    RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_0_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 11 ---
    .set pmpcfgi, CSR_PMPCFG0
    .rept UDB_NUM_PMP_ENTRIES/8
1:  LI(t2, 1 << 11)
    RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_1_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 13 ---
    .set pmpcfgi, CSR_PMPCFG0
    .rept UDB_NUM_PMP_ENTRIES/8
1:  LI(t2, 1 << 13)
    RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_2_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 14 ---
    .set pmpcfgi, CSR_PMPCFG0
    .rept UDB_NUM_PMP_ENTRIES/8
1:  LI(t2, 1 << 14)
    RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_3_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 15 ---
    .set pmpcfgi, CSR_PMPCFG0
    .rept UDB_NUM_PMP_ENTRIES/8
1:  LI(t2, 1 << 15)
    RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_4_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 16 ---
    .set pmpcfgi, CSR_PMPCFG0
    .rept UDB_NUM_PMP_ENTRIES/8
1:  LI(t2, 1 << 16)
    RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_5_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    RVTEST_GOTO_MMODE

RVTEST_CODE_END
RVTEST_DATA_BEGIN

// Test case strings for reporting
test_0_str: .string "\"write walking-one bit 10 to even pmpcfg CSRs; cp: cp_pmpcfg_walk\""
test_1_str: .string "\"write walking-one bit 11 to even pmpcfg CSRs; cp: cp_pmpcfg_walk\""
test_2_str: .string "\"write walking-one bit 13 to even pmpcfg CSRs; cp: cp_pmpcfg_walk\""
test_3_str: .string "\"write walking-one bit 14 to even pmpcfg CSRs; cp: cp_pmpcfg_walk\""
test_4_str: .string "\"write walking-one bit 15 to even pmpcfg CSRs; cp: cp_pmpcfg_walk\""
test_5_str: .string "\"write walking-one bit 16 to even pmpcfg CSRs; cp: cp_pmpcfg_walk\""

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
