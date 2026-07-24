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
//               systems. It specifically tests the Read, Write, and Execute
//               permissions for a designated memory region, ensuring that
//               the PMP settings are correctly applied and that the system
//               behaves as expected when accessing this region.
//
// Coverpoints :  cp_priority_off for PMPM is fully covered in this file.
//
// Test Cases  :  Testing that an OFF region does not match, and the first matching
//                region takes priority.
//                pmp0cfg0.L=1, pmpcfg0.A=OFF, pmpcfg0.XWR=000, pmpaddr0 = REGIONSTART
//                pmp1cfg0.L=1, pmpcfg1.A=NAPOT, pmpcfg1.XWR=101, pmpaddr1 = NAPOT(REGIONSTART, NAPOT_REGION_SIZE)
//                pmp2cfg0.L=1, pmpcfg2.A=OFF, pmpcfg2.XWR=000, pmpaddr2 = REGIONSTART
//                pmp3cfg0.L=1, pmpcfg3.A=NAPOT, pmpcfg3.XWR=111, pmpaddr3 = NAPOT(REGIONSTART, NAPOT_REGION_SIZE)
//                {lw, sw, jalr} to some address at REGIONSTART. It should succeed on
//                X and R but not W because it hits region 1.

// --------------------------------------------------------------------------------


##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['Sm']
# params:
#   MXLEN: 32
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv32i_zicsr_zifencei
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpsm_priority_off.S"
#define SIGUPD_COUNT 50


// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

#if UDB_PMP_GRANULARITY > 3
  #define NAPOT_REGION_SIZE         (1 << (UDB_PMP_GRANULARITY))
  #define NAPOT_ADDR_TRAILING_ONES  ((1 << (UDB_PMP_GRANULARITY - 3)) - 1)
#else
  #define NAPOT_REGION_SIZE         (1 << (UDB_PMP_GRANULARITY + 1))
  #define NAPOT_ADDR_TRAILING_ONES  0
#endif

.macro VERIFICATION_RWX ADDRESS TEST_CASE

    // Execution Access Check
    LA (a4, \ADDRESS)
    LA(x1, 1f)                          // Store the return Address in x1
    RVTEST_FENCEI                              // sync I-cache: a prior store may have updated this executable region
    \TEST_CASE\()_3:
    jalr ra, 0(a4)
    nop
    nop
1:
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)                 // Signature update

    LI(a4, NOP)                                              // Value to write (NOP)
    // Store Access Check
    LA(a5, \ADDRESS)                                      // Address to be verified

    \TEST_CASE\()_1:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)

    LA(a5, \ADDRESS)                                      // Address to be verified

    \TEST_CASE\()_2:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)                 // Signature update

.endm

main:
    // Loop to SET ALL pmpcfg REGs to zero
    .set pmpcfgi, CSR_PMPCFG0
    .rept UDB_NUM_PMP_ENTRIES/4
    csrw pmpcfgi , x0
    .set pmpcfgi, pmpcfgi+1
    .endr

    // Loop to SET ALL pmpaddr REGs to zero
    .set pmpaddri, CSR_PMPADDR0
    .rept UDB_NUM_PMP_ENTRIES
    csrw pmpaddri, x0
    .set pmpaddri, pmpaddri+1
    .endr

#define PMPREGION0_LXWR_1000 ((((PMP_L                            )&0xFF) << PMP0_CFG_SHIFT))
#define PMPREGION1_LXWR_1101 ((((PMP_L|PMP_R|      PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION2_LXWR_1000 ((((PMP_L                            )&0xFF) << PMP2_CFG_SHIFT))
#define PMPREGION3_LXWR_1111 ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT))


    RVTEST_PMP_SET_BACKGROUND x4

    // pmpaddr0 and pmpaddr2: OFF regions
    // pmpaddr1 and pmpaddr3: NAPOT regions of size NAPOT_REGION_SIZE covering REGIONSTART.
    LA(x5, TEST_FOR_EXECUTION)
    srl x5, x5, PMP_SHIFT
    csrw pmpaddr0, x5
    csrw pmpaddr2, x5

    LI(x6, NAPOT_ADDR_TRAILING_ONES)
    or x5, x5, x6
    csrw pmpaddr1, x5
    csrw pmpaddr3, x5

//                                          Verification Section
// Test Case: 1 : OFF region does not match, and the first matching region takes priority.

    // Setting pmpcfg0.L = 1, pmpcfg0.A = {NAPOT,OFF,NAPOT,OFF}, pmpcfg0.XWR = {111,000,101,000}
    LI(x4, PMPREGION3_LXWR_1111|PMPREGION2_LXWR_1000|PMPREGION1_LXWR_1101|PMPREGION0_LXWR_1000)
    csrw pmpcfg0, x4

    VERIFICATION_RWX   TEST_FOR_EXECUTION, test_1

RVTEST_CODE_END

RVTEST_DATA_BEGIN
.p2align 4

// Test case strings for reporting
test_1_str: .string "\"test: 1; cp: pmpm_priority_off_sw\""
test_2_str: .string "\"test: 2; cp: pmpm_priority_off_lw\""
test_3_str: .string "\"test: 2; cp: pmpm_priority_off_jalr\""

.p2align 12
TEST_FOR_EXECUTION_0:
    .rept PMP_NAPOT_REGION_PAD_WORDS                    // NAPOT-safe return fillers: puts TEST_FOR_EXECUTION at PMP_NAPOT_REGION_START
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
