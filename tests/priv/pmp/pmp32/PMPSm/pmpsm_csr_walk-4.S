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
//               systems. It evaluates RWX permissions at different granularity
//               levels (byte, half-word, word, double word) and across various
//               PMP configurations. The test adheres to the RISC-V Privileged
//               Specification v1.12 and includes:
//               - Comprehensive RWX checks for multiple PMP regions.
//
// Coverpoints : cp_pmpcfg_walk and cp_pmpaddr_walk for PMPM is fully covered in
//               this test file.
//
// Test Cases  : Test pmpaddr access. No background region, writing all 1s,
//               walking 1s, all 0s to all defined pmpaddr CSRs. Test pmpcfg access,
//               writing walking 1s from lsb to msb (XLEN-1) to pmpcfg CSRs 0, 2 and
//               writing 0 to pmpcfg 1, 3. If 64 CSRs are supported, doing same
//               with 4, 6, 8, 10, 12, 14; and 5, 7, 9, 11, 13, 15.
// --------------------------------------------------------------------------------
##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['I','Sm']
# params:
#   MXLEN: 32
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv32i_zicsr
##### END_TEST_CONFIG #####
// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpsm_csr_walk-04.S"
#define SIGUPD_COUNT 500

// Enable trap handler
#define rvtest_mtrap_routine
#define RVTEST_PRIV_TEST

// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

main:
    RVTEST_GOTO_MMODE

    // -----------------------------------------------------------------------
    // SET ALL pmpaddr REGs to zeros
    // -----------------------------------------------------------------------
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
    csrw pmpaddri, x0
    .set pmpaddri, pmpaddri+1
    .endr

    // -----------------------------------------------------------------------
    // SET ALL pmpaddr REGs to ones
    // -----------------------------------------------------------------------
    li t0, -1
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
    csrw pmpaddri, t0
    .set pmpaddri, pmpaddri+1
    .endr

    // -----------------------------------------------------------------------
    // SET ALL pmpcfg REGs to zero
    // -----------------------------------------------------------------------
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/4
    csrw pmpcfgi, x0
    .set pmpcfgi, pmpcfgi+1
    .endr

    // -----------------------------------------------------------------------
    // Walking ones through pmpaddr registers — bits 0..31 fully unrolled.
    //
    // Label strategy: inside each .rept block we place a GAS numeric local
    // label "1:" before the macro call and pass "1b" (the most recently
    // defined instance of label 1) as the label argument.  GAS creates a
    // fresh, unique symbol for every occurrence of a numeric label, so
    // RVTEST_SIGUPD_CSR_WRITE receives a distinct label each iteration with
    // no name collisions and no branch instructions.
    // -----------------------------------------------------------------------

    // --- pmpaddr walking ones, bit 21 ---
    li t2, (1 << 21)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_1_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 22 ---
    li t2, (1 << 22)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_2_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 23 ---
    li t2, (1 << 23)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_3_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 24 ---
    li t2, (1 << 24)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_4_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 25 ---
    li t2, (1 << 25)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_5_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 26 ---
    li t2, (1 << 26)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_6_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 27 ---
    li t2, (1 << 27)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_7_str)
    .set pmpaddri, pmpaddri+1
    .endr

    RVTEST_GOTO_MMODE

RVTEST_CODE_END
RVTEST_DATA_BEGIN

// Test case strings for reporting
test_1_str: .string "\"test: 1; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_22\""
test_2_str: .string "\"test: 2; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_23\""
test_3_str: .string "\"test: 3; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_24\""
test_4_str: .string "\"test: 4; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_25\""
test_5_str: .string "\"test: 5; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_26\""
test_6_str: .string "\"test: 6; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_27\""
test_7_str: .string "\"test: 7; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_28\""

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

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
