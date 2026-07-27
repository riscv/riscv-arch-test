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
// Coverpoints : cp_pmpcfg_walk and cp_pmpaddr_walk for PMPM is partially in
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
# MARCH: rv32i_zicsr_zifencei
##### END_TEST_CONFIG #####
// Define the size of the signature region
#define SIGUPD_COUNT 2000

// Enable trap handler
#define RVTEST_PRIV_TEST

// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

main:
    RVTEST_GOTO_MMODE


    // -----------------------------------------------------------------------
    // UDB_NUM_PMP_ENTRIES/8 gives the count of even cfg registers:
    //   16 PMPs → 2 even regs (pmpcfg0, pmpcfg2)
    //   64 PMPs → 8 even regs (pmpcfg0 .. pmpcfg14, step 2)
    // -----------------------------------------------------------------------

    // --- pmpcfg even walking ones, bit 31 ---
    .set pmpcfgi, CSR_PMPCFG0
    .rept UDB_NUM_PMP_ENTRIES/8
1:  LI(t2, 1 << 31)
    RVTEST_SIGUPD_CSR_WRITE(pmpcfgi, t2, 1b, test_1_str)
    .set pmpcfgi, pmpcfgi+2
    .endr

    RVTEST_GOTO_MMODE

RVTEST_CODE_END
RVTEST_DATA_BEGIN

// Test case strings for reporting
test_1_str: .string "\"test: 1; cp: cp_pmpcfg_walk_and_cp_pmpaddr_walk_test_64\""

.p2align 12
TEST_FOR_EXECUTION_0:
    .rept (1 << (UDB_PMP_GRANULARITY - 2))              // one PMP granule of jr-ra fillers: puts TEST_FOR_EXECUTION on the next granule boundary (= PMP_REGION_START at coverage grain 2), while staying naturally aligned for NAPOT at larger grains
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
