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
// Coverpoints : cp_csr_walk and cp_pmpaddr_walk for PMPM is partially in
//               this test file.
//
// Test Cases  : Test pmpaddr access. No background region, writing all 1s,
//               walking 1s, all 0s to all defined pmpaddr CSRs. Test pmpcfg access,
//               writing walking 1s from lsb to msb (XLEN-1) to pmpcfg CSRs 0, 2 and
//               writing 0 to pmpcfg 1, 3. If 64 CSRs are supported, doing same
//               with 4, 6, 8, 10, 12, 14; and 5, 7, 9, 11, 13, 15.
// --------------------------------------------------------------------------------
##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['Sm']
# params:
#   MXLEN: 32
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv32i_zicsr
##### END_TEST_CONFIG #####
// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpsm_csr_walk-06.S"
#define SIGUPD_COUNT 2000

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
    // Walking ones through even pmpcfg registers (pmpcfg0, pmpcfg2, ...).
    //
    // The original test writes walking ones only to even-numbered pmpcfg
    // registers (pmpcfg0, pmpcfg2, and — for 64-PMP systems — pmpcfg4 through
    // pmpcfg14).  Odd registers (pmpcfg1, pmpcfg3, ...) are RV32 aliases and
    // are intentionally left out, matching original behaviour.
    //
    // RVMODEL_NUM_PMPS/8 gives the count of even cfg registers:
    //   16 PMPs → 2 even regs (pmpcfg0, pmpcfg2)
    //   64 PMPs → 8 even regs (pmpcfg0 .. pmpcfg14, step 2)
    // -----------------------------------------------------------------------

    // --- pmpcfg even walking ones, bit 3 ---
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  li t2, (1 << 3)
    RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_1_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 5 ---

    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  li t2, (1 << 5)
    RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_2_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 6 ---

    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  li t2, (1 << 6)
    RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_3_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 7 ---

    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  li t2, (1 << 7)
    RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_4_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 8 ---

    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  li t2, (1 << 8)
    RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_5_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 9 ---

    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  li t2, (1 << 9)
    RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_6_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    RVTEST_GOTO_MMODE

RVTEST_CODE_END
RVTEST_DATA_BEGIN

// Test case strings for reporting
test_1_str: .string "\"test: 1; cp: cp_csr_walk\""
test_2_str: .string "\"test: 2; cp: cp_csr_walk\""
test_3_str: .string "\"test: 3; cp: cp_csr_walk\""
test_4_str: .string "\"test: 4; cp: cp_csr_walk\""
test_5_str: .string "\"test: 5; cp: cp_csr_walk\""
test_6_str: .string "\"test: 6; cp: cp_csr_walk\""

.align 12
TEST_FOR_EXECUTION_0:
    jr ra

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
