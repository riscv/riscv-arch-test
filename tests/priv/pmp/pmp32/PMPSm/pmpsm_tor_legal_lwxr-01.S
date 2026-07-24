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
// Coverpoints : cp_cfg_A_tor for PMPM is partially covered in this test file.
//
// Test Cases  : Checking XWR controls accesses in matching TOR region. With
//               pmpcfg_i.L =1, pmpcfg_i.A = TOR, all legal pmpcfg_i.XWR,
//               default TOR region, address-g in pmpaddr_i-1: making {lw,sw,jalr}
//               address, address-4, address-g, address-g-4.  Observing proper
//               access faults for restricted regions.
// --------------------------------------------------------------------------------


##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['Sm']
# params:
#   MXLEN: 32
#   NUM_PMP_ENTRIES: '>0'
#   PMP_TOR_SUPPORTED: true
# MARCH: rv32i_zicsr_zifencei
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpsm_tor_legal_lwxr.S"
#define SIGUPD_COUNT 100


// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

#define g    (1<<(UDB_PMP_GRANULARITY))

.macro VERIFICATION_RWX ADDRESS TEST_CASE

    RVTEST_FENCEI

    // Execution Access Check
    LA (a4, \ADDRESS)
    LA(x1, 1f)                          // Store the return Address in x1
    jalr ra, 0(a4)
    nop
    nop
1:
    nop
    nop

    addi a4, a4, -4                     // REGIONSTART - 4
    LA(x1, 2f)                          // Store the return Address in x1
    jalr ra, 0(a4)
    nop
    nop
2:
    nop
    nop

    addi a4, a4, 8                      // REGIONSTART + 4
    LA(x1, 3f)                          // Store the return Address in x1
    jalr ra, 0(a4)
    nop
    nop
3:
    nop
    nop

    LA (a4, \ADDRESS)
    LI(t0, g)
    add    a4, a4, t0
    addi a4, a4, -4                     // REGIONSTART + g - 4
    LA(x1, 4f)                          // Store the return Address in x1
    jalr ra, 0(a4)
    nop
    nop
4:
    nop
    nop

    addi a4, a4, 4                      // REGIONSTART + g
    LA(x1, 5f)                          // Store the return Address in x1
    jalr ra, 0(a4)
    nop
    nop
5:
    nop
    nop

    LI(a4, NOP)                                             // Value to write (NOP)
    // Store Access Check
    LA(a5, \ADDRESS)                                        // Address to be verified

    \TEST_CASE\()_1:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)

    addi a5, a5, -4                                         // REGIONSTART - 4

    \TEST_CASE\()_2:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)

    addi a5, a5, 8                                          // REGIONSTART + 4

    \TEST_CASE\()_3:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)

    LA (a5, \ADDRESS)
    LI(t0, g)
    add    a5, a5, t0
    addi a5, a5, -4                     // REGIONSTART + g - 4

    \TEST_CASE\()_4:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_4, test_4_str)

    addi a5, a5, 4                                          // REGIONSTART + g

    \TEST_CASE\()_5:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_5, test_5_str)

    LA(a5, \ADDRESS)                                        // Address to be verified

    \TEST_CASE\()_6:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_6, test_6_str)                                   // Signature update

    addi a5, a5, -4                                         // REGIONSTART - 4

    \TEST_CASE\()_7:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_7, test_7_str)                                   // Signature update

    addi a5, a5, 8                                          // REGIONSTART + 4

    \TEST_CASE\()_8:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_8, test_8_str)                                   // Signature update

    LA (a5, \ADDRESS)
    LI(t0, g)
    add    a5, a5, t0
    addi a5, a5, -4                     // REGIONSTART + g - 4

    \TEST_CASE\()_9:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_9, test_9_str)                                   // Signature update

    LA (a5, \ADDRESS)
    LI(t0, g)
    add    a5, a5, t0                     // REGIONSTART + g

    \TEST_CASE\()_10:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_10, test_10_str)                                   // Signature update

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

#define PMPREGION_LXWR_1000 ((((PMP_L|                  PMP_TOR  )&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LXWR_1001 ((((PMP_L|PMP_R|            PMP_TOR  )&0xFF) << PMP3_CFG_SHIFT))
#define PMPREGION_LXWR_1011 ((((PMP_L|PMP_R|PMP_W      |PMP_TOR  )&0xFF) << PMP1_CFG_SHIFT))
#define REGIONSTART         TEST_FOR_EXECUTION

    RVTEST_PMP_SET_BACKGROUND x4

    LA(x4, TEST_FOR_EXECUTION)
    LI(t0, g)
    add x5, x4, t0
    srl x4, x4, PMP_SHIFT
    srl x5, x5, PMP_SHIFT

    .set pmpaddri, CSR_PMPADDR0
    .rept 3
    csrw pmpaddri, x4
    .set pmpaddri, pmpaddri+1
    csrw pmpaddri, x5
    .set pmpaddri, pmpaddri+1
    .endr
//                                          Verification Section
// Test Case: 1 : L -> 1 and No Permissions given to the PMP Region 5

    LA(x6, TEST_FOR_EXECUTION)
    LI(t0, g)
    add x6, x6, t0
    srl x6, x6, PMP_SHIFT
    csrw pmpaddr5, x6
    LA(x5, TEST_FOR_EXECUTION)
    srl x5, x5, PMP_SHIFT
    csrw pmpaddr4, x5

    LI(x4, PMPREGION_LXWR_1000)
    csrw pmpcfg1, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_1

// Test Case: 2 : L -> 1 and R Permissions given to the PMP Region 3

    LA(x6, TEST_FOR_EXECUTION)
    LI(t0, g)
    add x6, x6, t0
    srl x6, x6, PMP_SHIFT
    csrw pmpaddr3, x6
    LA(x5, TEST_FOR_EXECUTION)
    srl x5, x5, PMP_SHIFT
    csrw pmpaddr2, x5

    LI(x4, PMPREGION_LXWR_1001)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_2

// Test Case: 3 : L -> 1 and WR Permissions given to the PMP Region 1

    LA(x6, TEST_FOR_EXECUTION)
    LI(t0, g)
    add x6, x6, t0
    srl x6, x6, PMP_SHIFT
    csrw pmpaddr1, x6
    LA(x5, TEST_FOR_EXECUTION)
    srl x5, x5, PMP_SHIFT
    csrw pmpaddr0, x5

    LI(x4, PMPREGION_LXWR_1011)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_3

RVTEST_CODE_END

RVTEST_DATA_BEGIN
.p2align 4

// Test case strings for reporting
test_1_str:  .string "\"test: 1;  cp: pmpm_aligned_sw_address\""
test_2_str:  .string "\"test: 2;  cp: pmpm_aligned_sw_address-4\""
test_3_str:  .string "\"test: 3;  cp: pmpm_aligned_sw_address+4\""
test_4_str:  .string "\"test: 4;  cp: pmpm_aligned_sw_address+g-4\""
test_5_str:  .string "\"test: 5;  cp: pmpm_aligned_sw_address+g\""

test_6_str:  .string "\"test: 6;  cp: pmpm_aligned_lw_address\""
test_7_str:  .string "\"test: 7;  cp: pmpm_aligned_lw_address-4\""
test_8_str:  .string "\"test: 8;  cp: pmpm_aligned_lw_address+4\""
test_9_str:  .string "\"test: 9;  cp: pmpm_aligned_lw_address+g-4\""
test_10_str: .string "\"test: 10; cp: pmpm_aligned_lw_address+g\""

.p2align 12
.p2align (UDB_PMP_GRANULARITY)
TEST_FOR_EXECUTION_0:
    .rept ((1<<(UDB_PMP_GRANULARITY))>>2)
    jr ra
    .endr

.p2align (UDB_PMP_GRANULARITY)
TEST_FOR_EXECUTION:
    .rept ((1<<(UDB_PMP_GRANULARITY))>>2)
    jr ra
    .endr

RETURN_INSTRUCTION:
    nop
    nop
    jr ra                                                        // Get back to the point from where TEST_FOR_EXECUTION was called.

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
