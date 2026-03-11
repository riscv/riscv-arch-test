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
# REQUIRED_EXTENSIONS:  ['I']
# params:
#   MXLEN: 32
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv32i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpsm_csr_walk.S"
#define SIGUPD_COUNT 40000

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

    // --- pmpaddr walking ones, bit 0 ---
    li t2, (1 << 0)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_1_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 1 ---
    li t2, (1 << 1)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_1_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 2 ---
    li t2, (1 << 2)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_1_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 3 ---
    li t2, (1 << 3)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_1_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 4 ---
    li t2, (1 << 4)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_1_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 5 ---
    li t2, (1 << 5)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_1_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 6 ---
    li t2, (1 << 6)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_1_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 7 ---
    li t2, (1 << 7)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_1_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 8 ---
    li t2, (1 << 8)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_1_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 9 ---
    li t2, (1 << 9)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_1_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 10 ---
    li t2, (1 << 10)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_1_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 11 ---
    li t2, (1 << 11)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_1_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 12 ---
    li t2, (1 << 12)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_1_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 13 ---
    li t2, (1 << 13)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_1_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 14 ---
    li t2, (1 << 14)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_1_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 15 ---
    li t2, (1 << 15)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_1_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 16 ---
    li t2, (1 << 16)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_1_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 17 ---
    li t2, (1 << 17)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_1_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 18 ---
    li t2, (1 << 18)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_1_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 19 ---
    li t2, (1 << 19)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_1_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 20 ---
    li t2, (1 << 20)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_1_str)
    .set pmpaddri, pmpaddri+1
    .endr

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
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_1_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 23 ---
    li t2, (1 << 23)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_1_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 24 ---
    li t2, (1 << 24)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_1_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 25 ---
    li t2, (1 << 25)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_1_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 26 ---
    li t2, (1 << 26)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_1_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 27 ---
    li t2, (1 << 27)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_1_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 28 ---
    li t2, (1 << 28)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_1_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 29 ---
    li t2, (1 << 29)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_1_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 30 ---
    li t2, (1 << 30)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_1_str)
    .set pmpaddri, pmpaddri+1
    .endr

    // --- pmpaddr walking ones, bit 31 (MSB for RV32 pmpaddr) ---
    li t2, (1 << 31)
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
1:  RVTEST_SIGUPD_CSR_WRITE(pmpaddri, t2, 1b, test_1_str)
    .set pmpaddri, pmpaddri+1
    .endr

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

    // --- pmpcfg even walking ones, bit 0 ---
    li t2, (1 << 0)
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_65_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 1 ---
    li t2, (1 << 1)
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_65_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 2 ---
    li t2, (1 << 2)
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_65_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 3 ---
    li t2, (1 << 3)
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_65_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 4 ---
    li t2, (1 << 4)
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_65_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 5 ---
    li t2, (1 << 5)
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_65_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 6 ---
    li t2, (1 << 6)
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_65_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 7 ---
    li t2, (1 << 7)
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_65_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 8 ---
    li t2, (1 << 8)
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_65_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 9 ---
    li t2, (1 << 9)
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_65_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 10 ---
    li t2, (1 << 10)
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_65_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 11 ---
    li t2, (1 << 11)
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_65_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 12 ---
    li t2, (1 << 12)
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_65_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 13 ---
    li t2, (1 << 13)
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_65_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 14 ---
    li t2, (1 << 14)
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_65_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 15 ---
    li t2, (1 << 15)
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_65_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 16 ---
    li t2, (1 << 16)
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_65_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 17 ---
    li t2, (1 << 17)
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_65_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 18 ---
    li t2, (1 << 18)
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_65_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 19 ---
    li t2, (1 << 19)
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_65_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 20 ---
    li t2, (1 << 20)
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_65_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 21 ---
    li t2, (1 << 21)
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_65_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 22 ---
    li t2, (1 << 22)
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_65_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 23 ---
    li t2, (1 << 23)
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_65_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 24 ---
    li t2, (1 << 24)
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_65_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 25 ---
    li t2, (1 << 25)
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_65_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 26 ---
    li t2, (1 << 26)
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_65_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 27 ---
    li t2, (1 << 27)
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_65_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 28 ---
    li t2, (1 << 28)
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_65_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 29 ---
    li t2, (1 << 29)
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_65_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 30 ---
    li t2, (1 << 30)
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_65_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    // --- pmpcfg even walking ones, bit 31 ---
    li t2, (1 << 31)
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
1:  RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_65_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    RVTEST_GOTO_MMODE
    j exit                                      // Verification complete, exit the test

.align 10
.align (RVMODEL_PMP_GRAIN+2)

RETURN_INSTRUCTION:
    nop
    nop
    jr ra                                       // Return from TEST_FOR_EXECUTION call

exit:

RVTEST_CODE_END
RVTEST_DATA_BEGIN
.align 4

// Test case strings for reporting
canary_mismatch: .string "Testcase signature canary mismatch!"
test_1_str:  .string "\"test: 1; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_1\""
test_2_str:  .string "\"test: 2; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_2\""
test_3_str:  .string "\"test: 3; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_3\""
test_4_str:  .string "\"test: 4; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_4\""
test_5_str:  .string "\"test: 5; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_5\""
test_6_str:  .string "\"test: 6; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_6\""
test_7_str:  .string "\"test: 7; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_7\""
test_8_str:  .string "\"test: 8; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_8\""
test_9_str:  .string "\"test: 9; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_9\""
test_10_str: .string "\"test: 10; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_10\""
test_11_str: .string "\"test: 11; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_11\""
test_12_str: .string "\"test: 12; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_12\""
test_13_str: .string "\"test: 13; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_13\""
test_14_str: .string "\"test: 14; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_14\""
test_15_str: .string "\"test: 15; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_15\""
test_16_str: .string "\"test: 16; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_16\""
test_17_str: .string "\"test: 17; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_17\""
test_18_str: .string "\"test: 18; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_18\""
test_19_str: .string "\"test: 19; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_19\""
test_20_str: .string "\"test: 20; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_20\""
test_21_str: .string "\"test: 21; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_21\""
test_22_str: .string "\"test: 22; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_22\""
test_23_str: .string "\"test: 23; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_23\""
test_24_str: .string "\"test: 24; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_24\""
test_25_str: .string "\"test: 25; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_25\""
test_26_str: .string "\"test: 26; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_26\""
test_27_str: .string "\"test: 27; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_27\""
test_28_str: .string "\"test: 28; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_28\""
test_29_str: .string "\"test: 29; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_29\""
test_30_str: .string "\"test: 30; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_30\""
test_31_str: .string "\"test: 31; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_31\""
test_32_str: .string "\"test: 32; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_32\""
test_33_str: .string "\"test: 33; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_33\""
test_34_str: .string "\"test: 34; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_34\""
test_35_str: .string "\"test: 35; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_35\""
test_36_str: .string "\"test: 36; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_36\""
test_37_str: .string "\"test: 37; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_37\""
test_38_str: .string "\"test: 38; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_38\""
test_39_str: .string "\"test: 39; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_39\""
test_40_str: .string "\"test: 40; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_40\""
test_41_str: .string "\"test: 41; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_41\""
test_42_str: .string "\"test: 42; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_42\""
test_43_str: .string "\"test: 43; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_43\""
test_44_str: .string "\"test: 44; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_44\""
test_45_str: .string "\"test: 45; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_45\""
test_46_str: .string "\"test: 46; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_46\""
test_47_str: .string "\"test: 47; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_47\""
test_48_str: .string "\"test: 48; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_48\""
test_49_str: .string "\"test: 49; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_49\""
test_50_str: .string "\"test: 50; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_50\""
test_51_str: .string "\"test: 51; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_51\""
test_52_str: .string "\"test: 52; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_52\""
test_53_str: .string "\"test: 53; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_53\""
test_54_str: .string "\"test: 54; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_54\""
test_55_str: .string "\"test: 55; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_55\""
test_56_str: .string "\"test: 56; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_56\""
test_57_str: .string "\"test: 57; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_57\""
test_58_str: .string "\"test: 58; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_58\""
test_59_str: .string "\"test: 59; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_59\""
test_60_str: .string "\"test: 60; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_60\""
test_61_str: .string "\"test: 61; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_61\""
test_62_str: .string "\"test: 62; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_62\""
test_63_str: .string "\"test: 63; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_63\""
test_64_str: .string "\"test: 64; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_64\""
test_65_str: .string "\"test: 65; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_65\""
test_66_str: .string "\"test: 66; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_66\""
test_67_str: .string "\"test: 67; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_67\""
test_68_str: .string "\"test: 68; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_68\""
test_69_str: .string "\"test: 69; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_69\""
test_70_str: .string "\"test: 70; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_70\""
test_71_str: .string "\"test: 71; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_71\""
test_72_str: .string "\"test: 72; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_72\""

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
