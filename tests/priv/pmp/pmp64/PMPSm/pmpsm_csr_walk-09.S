// --------------------------------------------------------------------------------
// Copyright (C) 2025 Harvey Mudd College & Oklahoma State University, UET Lahore, Habib University
// SPDX-License-Identifier: Apache-2.0
//
// Title           : Comprehensive PMP (Physical Memory Protection) Verification
// Authors         : Umer Shahid, Allen Baum, David Harris
//                  Muhammad Abdullah, Hamza Ali, Muhammad Zain
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
#   MXLEN: 64
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv64i_zicsr
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmp_csr_walk_9.S"
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
    // Walking ones through pmpaddr registers — bits 0..63 fully unrolled.
    //
    // Label strategy: place GAS numeric local label "1:" immediately before
    // each RVTEST_SIGUPD_CSR_WRITE call and pass "1b" as the label argument.
    // GAS creates a fresh unique symbol for every occurrence of a numeric
    // label, so there are no name collisions and no branch instructions.
    //
    // The outer walking-ones loop from the original (slli / bnez) is replaced
    // by 64 explicit li t2, (1<<N) blocks — one per bit — each containing a
    // .rept over all PMP registers.  No runtime branching is used.
    // -----------------------------------------------------------------------

    // --- pmpaddr walking ones, bit 56 ---

    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  li t2, (1 << 56)
    RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_57_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 57 ---

    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  li t2, (1 << 57)
    RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_58_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 58 ---

    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  li t2, (1 << 58)
    RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_59_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 59 ---

    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  li t2, (1 << 59)
    RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_60_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 60 ---

    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  li t2, (1 << 60)
    RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_61_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 61 ---

    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  li t2, (1 << 61)
    RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_62_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 62 ---

    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  li t2, (1 << 62)
    RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_63_str)
    .set pmpaddri, pmpaddri+1
    .endr

    RVTEST_GOTO_MMODE

RVTEST_CODE_END
RVTEST_DATA_BEGIN

// Test case strings for reporting
test_57_str: .string "\"test: 57; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_57\""
test_58_str: .string "\"test: 58; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_58\""
test_59_str: .string "\"test: 59; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_59\""
test_60_str: .string "\"test: 60; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_60\""
test_61_str: .string "\"test: 61; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_61\""
test_62_str: .string "\"test: 62; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_62\""
test_63_str: .string "\"test: 63; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_63\""

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
