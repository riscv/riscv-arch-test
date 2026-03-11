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
// Coverpoints : cp_cfg_L_modify for PMPM is partially covered in this test file.
//
// Test Cases  : Checking that pmpcfg and pmpaddr are unwritable when L = 1.
//               With pmpcfg_i.L ={0/1}, pmpcfg_i.A = OFF, pmpcfg_i.XWR = 111,
//               pmpaddr_i = 0x100, trying to change pmpcfg_i to 000000000,
//               and to change pmpaddr_i to 0s, and reading these back.
//               When L = 1, should be unchanged because of lock.
//               When L = 0, changeable.
//
//               Checking that pmpcfg and pmpaddr of previous region are unwritable
//               when L = 1. With pmpcfg_i.L={0/1}, pmpcfg_i.A=OFF, pmpcfg_i.XWR=111,
//               pmpaddr_i = 0x100, pmpcfg_i-1.L=0 trying to change pmpcfg_i-1 to
//               00000111, and to change pmpaddr_i-1 to 1s and reading these back.
//               pmpaddr_i-1 should be unchanged because of lock iff pmpcfg_i.A = TOR,
//               otherwise change. pmpcfg_i-1 is changeable independent of pmpcfg_i.A.
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
#define TEST_FILE "pmpsm_cfg_L_modify_off.S"
#define SIGUPD_COUNT 50

// Enable trap handler
#define rvtest_mtrap_routine
#define RVTEST_PRIV_TEST

#define SKIP_MEPC

// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

main:
    // Loop to SET ALL pmpcfg REGs to zero
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/4
    csrw pmpcfgi , x0
    .set pmpcfgi, pmpcfgi+1
    .endr

    // Loop to SET ALL pmpaddr REGs to zero
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
    csrw pmpaddri, x0
    .set pmpaddri, pmpaddri+1
    .endr

#define PMP_REGION_GLOBAL   ((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF)  // Background region with RWX enable.
#define PMPADDRESS_TOP_GLOBAL       -1                                              // All memory region


    LA(x4, PMPADDRESS_TOP_GLOBAL)
    csrw    pmpaddr15, x4

    //Lock the Background region.
    LI(x4, (PMP_REGION_GLOBAL << PMP3_CFG_SHIFT))
    csrw pmpcfg3, x4

//                                          Verification Section
// Test Case 1 : Setting region 1 to be OFF with L->0, XWR->111 and pmpaddr->0x100

    addi x4, x0, 0x100
    test_1:
        # Write x4 to pmpaddr1, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpaddr1, x4, test_1, test_1_str)

    LI(x4, ((PMP_R|PMP_W|PMP_X)&0xFF) << PMP1_CFG_SHIFT)
    test_2:
        # Write x4 to pmpcfg0, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg0, x4, test_2, test_2_str)

        // Now trying to change pmp0cfg0 to 000000111, and to change pmpaddr0 to 1s.

    addi x5, x4, 7
    test_3:
        # Write x5 to pmpcfg0, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg0, x5, test_3, test_3_str)

    addi x4, x0,-1
    test_4:
        # Write x4 to pmpaddr0, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpaddr0, x4, test_4, test_4_str)

// Now trying to change pmp1cfg0 to 000000000, and to change pmpaddr1 to 0s.

    test_5:
        # Write x0 to pmpaddr1, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpaddr1, x0, test_5, test_5_str)

    test_6:
        # Write x0 to pmpcfg0, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg0, x0, test_6, test_6_str)


//--- Re-initialize the CSRs. ---
    test_7:
        # Write x0 to pmpaddr0, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpaddr0, x0, test_7, test_7_str)

    test_8:
        # Write x0 to pmpcfg0, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg0, x0, test_8, test_8_str)
    //-------------------------------


// Test Case 2 : Setting region 1 to be OFF with L->1, XWR->111 and pmpaddr->0x100

    addi x4, x0, 0x100
    test_9:
        # Write x4 to pmpaddr1, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpaddr1, x4, test_9, test_9_str)

    LI(x4, ((PMP_L|PMP_R|PMP_W|PMP_X)&0xFF) << PMP1_CFG_SHIFT)
    test_10:
        # Write x4 to pmpcfg0, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg0, x4, test_10, test_10_str)

        // Now trying to change pmp0cfg0 to 000000111, and to change pmpaddr0 to 1s.

    addi x5, x4, 7
    test_11:
        # Write x5 to pmpcfg0, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg0, x5, test_11, test_11_str)

    addi x4, x0,-1
    test_12:
        # Write x4 to pmpaddr0, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpaddr0, x4, test_12, test_12_str)

// Now trying to change pmp1cfg0 to 000000000, and to change pmpaddr1 to 0s.

    test_13:
        # Write x0 to pmpaddr1, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpaddr1, x0, test_13, test_13_str)

    test_14:
        # Write x0 to pmpcfg0, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg0, x0, test_14, test_14_str)

// --------------------------------------------------------------------------------

    j exit                                                      // Verification Complete, exit the test

.align 10
.align (RVMODEL_PMP_GRAIN+2)

exit:

RVTEST_CODE_END

RVTEST_DATA_BEGIN
.align 4

// Test case strings for reporting
canary_mismatch: .string "Testcase signature canary mismatch!"
test_1_str:  .string "\"test: 1; cp: cp_cfg_L_modify_1\""
test_2_str:  .string "\"test: 2; cp: cp_cfg_L_modify_2\""
test_3_str:  .string "\"test: 3; cp: cp_cfg_L_modify_3\""
test_4_str:  .string "\"test: 4; cp: cp_cfg_L_modify_4\""
test_5_str:  .string "\"test: 5; cp: cp_cfg_L_modify_5\""
test_6_str:  .string "\"test: 6; cp: cp_cfg_L_modify_6\""
test_7_str:  .string "\"test: 7; cp: cp_cfg_L_modify_7\""
test_8_str:  .string "\"test: 8; cp: cp_cfg_L_modify_8\""
test_9_str:  .string "\"test: 9; cp: cp_cfg_L_modify_9\""
test_10_str: .string "\"test: 10; cp: cp_cfg_L_modify_10\""
test_11_str: .string "\"test: 11; cp: cp_cfg_L_modify_11\""
test_12_str: .string "\"test: 12; cp: cp_cfg_L_modify_12\""
test_13_str: .string "\"test: 13; cp: cp_cfg_L_modify_13\""
test_14_str: .string "\"test: 14; cp: cp_cfg_L_modify_14\""

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
