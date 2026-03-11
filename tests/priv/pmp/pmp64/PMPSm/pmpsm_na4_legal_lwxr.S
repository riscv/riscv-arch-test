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
// Coverpoints : cp_cfg_A_na4 for PMPM is fully covered in this test file.
//
// Test Cases  : Checking XWR controls accesses in matching NA4 region. G=0 Only
//               with pmpcfg_i.L = 1, pmpcfg_i.A=NA4, all legal pmpcfg_i.XWR,
//               reasonable address in pmpaddr: making {lw, sw, jalr} at that
//               address, that address - 4, just beyond top of the region.
//               Observing proper access faults for restricted regions, and
//               accesses beyond the region and below the region should succeed
//               because the bckground region is set to RWX.

// --------------------------------------------------------------------------------

#define SKIP_MEPC
##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: ['I']
# params:
#   MXLEN: 64
#   NUM_PMP_ENTRIES: '>0'
# MARCH: rv64i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpsm_na4_legal_lwxr.S"
#define SIGUPD_COUNT 50

// Enable trap handler
#define rvtest_mtrap_routine
#define RVTEST_PRIV_TEST

// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

.macro VERIFICATION_RWX ADDRESS TEST_CASE

    LI(x4, 0xACCE)                        // Store a value which is to be checked in trap handler
    // Execution Access Check
    LA (a4, \ADDRESS)
    LA(x1, 1f)                            // Store the return Address in x1
    jalr ra, 0(a4)
    nop
    nop
1:
    nop
    nop

    LI(x4, 0xACCE)
    addi a4, a4, -4                     // REGIONSTART - 4
    LA(x1, 2f)                            // Store the return Address in x1
    jalr ra, 0(a4)
    nop
    nop
2:
    nop
    nop

    LI(x4, 0xACCE)
    addi a4, a4, 8                      // REGIONSTART + 4
    LA(x1, 3f)                            // Store the return Address in x1
    jalr ra, 0(a4)
    nop
    nop
3:
    nop
    nop

    LI(a4, DOUBLE_NOP)                                              // Value to write (DOUBLE_NOP)

    // Load & Store Access Check
    LA(a5, \ADDRESS)                                         // Address to be verified

    \TEST_CASE\()_1:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)

    \TEST_CASE\()_2:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)


    addi a5, a5, -4                                          // REGIONSTART - 4

    \TEST_CASE\()_3:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)

    \TEST_CASE\()_4:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_4, test_4_str)


    addi a5, a5, 8                                           // REGIONSTART + 4

    \TEST_CASE\()_5:
    sw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_5, test_5_str)

    \TEST_CASE\()_6:
    lw a4, 0(a5)
    nop
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_6, test_6_str)

.endm

main:
    // Loop to SET ALL pmpcfg REGs to zero
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/8
    csrw pmpcfgi , x0
    .set pmpcfgi, pmpcfgi+2
    .endr

    // Loop to SET ALL pmpaddr REGs to zero
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
    csrw pmpaddri, x0
    .set pmpaddri, pmpaddri+1
    .endr

#define PMP_REGION_GLOBAL    ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP7_CFG_SHIFT))  // Background region with RWX enable.
#define PMPREGION_LXWR_1000 ((((PMP_L|                  PMP_NA4  )&0xFF) << PMP5_CFG_SHIFT))
#define PMPREGION_LXWR_1001 ((((PMP_L|PMP_R|            PMP_NA4  )&0xFF) << PMP4_CFG_SHIFT))
#define PMPREGION_LXWR_1011 ((((PMP_L|PMP_R|PMP_W       |PMP_NA4  )&0xFF) << PMP3_CFG_SHIFT))
#define PMPREGION_LXWR_1100 ((((PMP_L|              PMP_X|PMP_NA4  )&0xFF) << PMP2_CFG_SHIFT))
#define PMPREGION_LXWR_1101 ((((PMP_L|PMP_R         |PMP_X|PMP_NA4  )&0xFF) << PMP1_CFG_SHIFT))
#define PMPREGION_LXWR_1111 ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NA4  )&0xFF) << PMP0_CFG_SHIFT))

#define PMPADDRESS_TOP_GLOBAL        -1                                                // All memory region
#define REGIONSTART        TEST_FOR_EXECUTION        // RAM_BASE_ADDR + PROGRAM_SIZE

    LA(x4, PMPADDRESS_TOP_GLOBAL)
    csrw     pmpaddr15, x4

    //Lock the Background region.
    LI(x4, PMP_REGION_GLOBAL)
    csrw pmpcfg2, x4

//                                            Verification Section
// Test Case: 1 : L -> 1 and No Permissions given to the PMP Region 5

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    csrw pmpaddr5, x5

    LI(x4, PMPREGION_LXWR_1000)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION,test_1

// Test Case: 2 : L -> 1 and R Permissions given to the PMP Region 4

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    csrw pmpaddr4, x5

    LI(x4, PMPREGION_LXWR_1001)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION,test_2

// Test Case: 3 : L -> 1 and WR Permissions given to the PMP Region 3

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    csrw pmpaddr3, x5

    LI(x4, PMPREGION_LXWR_1011)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION,test_3

// Test Case: 4 : L -> 1 and X Permissions given to the PMP Region 2

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    csrw pmpaddr2, x5

    LI(x4, PMPREGION_LXWR_1100)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION,test_4

// Test Case: 5 : L -> 1 and No Permissions given to the PMP Region 1

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    csrw pmpaddr1, x5

    LI(x4, PMPREGION_LXWR_1101)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION,test_5

// Test Case: 6 : L -> 1 and XWR Permissions given to the PMP Region 0

    LA(x5, REGIONSTART)
    srl x5, x5, PMP_SHIFT
    csrw pmpaddr0, x5

    LI(x4, PMPREGION_LXWR_1111)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION,test_6


    j exit                                                        // Verification Complete, exit the test

.align 12
TEST_FOR_EXECUTION:
    .rept (1<<(RVMODEL_PMP_GRAIN+2))
    nop
    .endr

RETURN_INSTRUCTION:
    nop
    nop
    jr ra                                                        // Get back to the point from where TEST_FOR_EXECUTION was called.

exit:

RVTEST_CODE_END
RVTEST_DATA_BEGIN
.align 4

// Test case strings for reporting
canary_mismatch: .string "Testcase signature canary mismatch!"
test_1_str: .string "\"test: 1; cp: cp_cfg_A_na4_sw_address\""
test_2_str: .string "\"test: 2; cp: cp_cfg_A_na4_lw_address\""

test_3_str: .string "\"test: 3; cp: cp_cfg_A_na4_sw_address-4\""
test_4_str: .string "\"test: 4; cp: cp_cfg_A_na4_lw_address-4\""

test_5_str: .string "\"test: 5; cp: cp_cfg_A_na4_sw_address+4\""
test_6_str: .string "\"test: 6; cp: cp_cfg_A_na4_lw_address+4\""


RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
