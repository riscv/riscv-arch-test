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
//               systems. It specifically tests the Read, Write, and Execute
//               permissions for a designated memory region, ensuring that
//               the PMP settings are correctly applied and that the system
//               behaves as expected when accessing this region.
//
// Coverpoints :  cp_priority for PMPM is fully covered in this file.
//
// Test Cases  :  Testing that first matching region has priority to determine
//                XWR. Set up 7 even/odd pairs of TOR regions, where each pair
//                starts (even) at the standard location and has pair i has size
//                i*g (in odd reg) so the regions partially overlap. Set the even
//                pmpcfg to 0 (OFF). Set the odd pmpcfg to TOR and cycle through
//                the 6 legal XWR values for each pair. Make {lw, sw, jalr} to
//                each of (PMP_writable_regs-1) addresses at end of each region.
//                Access fault if the relevant (highest priority) region prohibits
//                access.

// --------------------------------------------------------------------------------


##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['Sm']
# params:
#   MXLEN: 64
#   NUM_PMP_ENTRIES: '>0'
#   PMP_NAPOT_SUPPORTED: true
#   PMP_TOR_SUPPORTED: true
# MARCH: rv64i_zicsr_zifencei
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpsm_priority.S"
#define SIGUPD_COUNT 200


// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

#define g   (1 << (UDB_PMP_GRANULARITY))

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
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)


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
    .rept UDB_NUM_PMP_ENTRIES/8
    csrw pmpcfgi , x0
    .set pmpcfgi, pmpcfgi+2
    .endr

    // Loop to SET ALL pmpaddr REGs to zero
    .set pmpaddri, CSR_PMPADDR0
    .rept UDB_NUM_PMP_ENTRIES
    csrw pmpaddri, x0
    .set pmpaddri, pmpaddri+1
    .endr

#define PMP_REGION_GLOBAL    ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP7_CFG_SHIFT))  // Background region with RWX enable.
#define PMPREGION_LXWR_1000 ((((PMP_L|                  PMP_TOR  )&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LXWR_1101 ((((PMP_L|      PMP_R|PMP_X|PMP_TOR  )&0xFF) << PMP3_CFG_SHIFT))
#define PMPREGION_LXWR_1011 ((((PMP_L|PMP_R|PMP_W|      PMP_TOR  )&0xFF) << PMP5_CFG_SHIFT))
#define PMPREGION_LXWR_1100 ((((PMP_L|            PMP_X|PMP_TOR  )&0xFF) << PMP7_CFG_SHIFT))
#define PMPREGION_LXWR_1001 ((((PMP_L|PMP_R            |PMP_TOR  )&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LXWR_1111 ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_TOR  )&0xFF) << PMP3_CFG_SHIFT))

    LA(x4, -1)                      // All memory region
    csrw     pmpaddr15, x4

    //Lock the Background region.
    LI(x4, PMP_REGION_GLOBAL)
    csrw pmpcfg2, x4

    LA(x4, TEST_FOR_EXECUTION)
    srl x4, x4, PMP_SHIFT
    LI(t0, g)
    add x5, x0, t0

    // REGIONSTART in even PMPADDR
    .set pmpaddri, CSR_PMPADDR0
    .rept 7
    csrw pmpaddri, x4
    .set pmpaddri, pmpaddri+2
    .endr

    // REGIONSTART + i*g in odd PMPADDR. Uses t2 (not t0, which aliases x5 the
    // accumulator) so the per-iteration LI doesn't clobber the running total.
    LA(x5, TEST_FOR_EXECUTION)
    .set pmpaddri, CSR_PMPADDR0+1
    .rept 7
    LI(t2, g)
    add x5, x5, t2
    srl x6, x5, PMP_SHIFT
    csrw pmpaddri, x6
    .set pmpaddri, pmpaddri+2
    .endr

    // Setting the even pmpcfg to 0 and odd pmpcfg to TOR & and rotating through the 6 legal XWR values.
    LI(x4, (PMPREGION_LXWR_1100|PMPREGION_LXWR_1011|PMPREGION_LXWR_1101|PMPREGION_LXWR_1000))
    csrw pmpcfg0, x4
    LI(x4, (PMPREGION_LXWR_1000 << PMP4_CFG_SHIFT|PMPREGION_LXWR_1111|PMPREGION_LXWR_1001))
    csrw pmpcfg2, x4

//                                            Verification Section
// Test Case: 1 : Accessing at end of region with No Permissions

    VERIFICATION_RWX   (TEST_FOR_EXECUTION + g - 4), test_1

// Test Case: 2 : Accessing at end of region with XR Permissions

    VERIFICATION_RWX   (TEST_FOR_EXECUTION + 2*g - 4), test_2
// For larger UDB_PMP_GRANULARITY, it is raising
// relocation truncation error to fit: R_RISCV_JAL
// Regions get so large, trap handler, RVMODEL macros,
// and failure macros gets far apart and start raising errors
#if UDB_PMP_GRANULARITY == 2
// Test Case: 3 : Accessing at end of region with WR Permissions

    VERIFICATION_RWX   (TEST_FOR_EXECUTION + 3*g - 4), test_3

// Test Case: 4 : Accessing at end of region with X Permissions

    VERIFICATION_RWX   (TEST_FOR_EXECUTION + 4*g - 4), test_4

// Test Case: 5 : Accessing at end of region with R Permissions

    VERIFICATION_RWX   (TEST_FOR_EXECUTION + 5*g - 4), test_5

// Test Case: 6 : Accessing at end of region with XWR Permissions

    VERIFICATION_RWX   (TEST_FOR_EXECUTION + 6*g - 4), test_6

// Test Case: 6 : Accessing at end of region with No Permissions

    VERIFICATION_RWX   (TEST_FOR_EXECUTION + 7*g - 4), test_7
#endif
RVTEST_CODE_END

RVTEST_DATA_BEGIN
.p2align 4

// Test case strings for reporting
test_1_str: .string "\"test: 1; cp: pmpm_priority_sw\""
test_2_str: .string "\"test: 2; cp: pmpm_priority_lw\""
test_3_str: .string "\"test: 3; cp: pmpm_priority_jalr\""

.p2align 12
.p2align (UDB_PMP_GRANULARITY)
TEST_FOR_EXECUTION_0:
    .rept (1 << (UDB_PMP_GRANULARITY - 2))              // one PMP granule of return-instruction fillers: places the region on the next granule boundary (= PMP_REGION_START at coverage grain 2), grain-aligned at larger grains
    jr ra
    .endr

TEST_FOR_EXECUTION:
// For larger UDB_PMP_GRANUMARITY, it is raising
// relocation truncation error to fit: R_RISCV_JAL
// Regions get so large, trap handler, RVMODEL macros,
// and failure macros gets far apart and start raising errors
#if UDB_PMP_GRANULARITY == 2
    .rept (8*(1<<(UDB_PMP_GRANULARITY)))
#else
    .rept (2*(1<<(UDB_PMP_GRANULARITY)))
#endif
    nop
    .endr

RETURN_INSTRUCTION:
    nop
    nop
    jr ra                                                        // Get back to the point from where TEST_FOR_EXECUTION was called.

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
