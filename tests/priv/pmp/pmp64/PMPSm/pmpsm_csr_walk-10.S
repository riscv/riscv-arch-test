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
# REQUIRED_EXTENSIONS:  ['I']
# params:
#   MXLEN: 64
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv64i_zicsr
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmp_csr_walk_10.S"
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

    // --- pmpaddr walking ones, bit 63 (MSB for RV64) ---

    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  li t2, (1 << 63)
    RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_64_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // -----------------------------------------------------------------------
    // Walking ones through even pmpcfg registers (pmpcfg0, pmpcfg2, ...).
    //
    // On RV64 each pmpcfg register holds 8 PMP entries (64 bits wide).
    // Only even-numbered pmpcfg CSRs exist on RV64; odd ones are illegal.
    // The original test writes walking ones to: pmpcfg0, pmpcfg2, and (for
    // 64-PMP systems) pmpcfg4, pmpcfg6, pmpcfg8, pmpcfg10, pmpcfg12, pmpcfg14.
    //
    // Count of even pmpcfg registers:
    //   16 PMPs → 2  (pmpcfg0, pmpcfg2)
    //   64 PMPs → 8  (pmpcfg0 .. pmpcfg14, step 2)
    // = RVMODEL_NUM_PMPS / 8
    //
    // The original walking-ones loop ran for all 64 bits (bnez t2 terminates
    // when the shifted-out bit reaches zero).  We replace it with 64 explicit
    // li blocks — one per bit — each containing a .rept over all even cfg regs.
    // -----------------------------------------------------------------------

    // --- pmpcfg even walking ones, bit 0 ---

    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  li t2, (1 << 0)
    RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_65_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 1 ---

    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  li t2, (1 << 1)
    RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_66_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 2 ---

    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  li t2, (1 << 2)
    RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_67_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 3 ---

    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  li t2, (1 << 3)
    RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_68_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 4 ---

    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  li t2, (1 << 4)
    RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_69_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 5 ---

    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  li t2, (1 << 5)
    RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_70_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // -----------------------------------------------------------------------
    // SET ALL pmpcfg REGs to zero (placed after walking ones, matching
    // original test ordering)
    // -----------------------------------------------------------------------
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/4
    csrw pmpcfgi, x0
    .set pmpcfgi, pmpcfgi+1
    .endr

    RVTEST_GOTO_MMODE

RVTEST_CODE_END
RVTEST_DATA_BEGIN

// Test case strings for reporting
test_64_str: .string "\"test: 64; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_64\""
test_65_str: .string "\"test: 65; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_65\""
test_66_str: .string "\"test: 66; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_66\""
test_67_str: .string "\"test: 67; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_67\""
test_68_str: .string "\"test: 68; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_68\""
test_69_str: .string "\"test: 69; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_69\""
test_70_str: .string "\"test: 70; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_70\""

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
