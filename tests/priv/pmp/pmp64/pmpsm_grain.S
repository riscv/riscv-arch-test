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
//
// Coverpoints: cp_grain for PMPM is fully covered in this test file.
//
// Test case  : Checking that low bits read as 0/1s depending on grain and address
//                matching mode. Set up pmpcfg0.L = 0, pmpcfg.A = {OFF/NAPOT}, write
//                pmpaddr0 = {all 0s / all 1s / checkerboard}. Change pmpcfg.A to
//                {OFF/TOR/NAPOT} and read back pmpaddr0. Bottom G-1 bits always read
//                as 1s in NAPOT. Bottom G bits read as 0s in TOR/OFF.
// --------------------------------------------------------------------------------

#define SKIP_MEPC
##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: ['I','Smpmp']
# params:
#   MXLEN: 64
# MARCH: rv64i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpsm_grain.S"
#define SIGUPD_COUNT 50

// Enable trap handler
#define rvtest_mtrap_routine
#define RVTEST_PRIV_TEST

// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

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

#define PMP_REGION_GLOBAL    ((((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT) &0xFF) << PMP7_CFG_SHIFT))  // Background region with RWX enable.
#define PMPREGION_OFF          ((((     PMP_R|PMP_W|PMP_X)               &0xFF) << PMP0_CFG_SHIFT))
#define PMPREGION_NAPOT     ((((     PMP_R|PMP_W|PMP_X |PMP_NAPOT) &0xFF) << PMP0_CFG_SHIFT))
#define PMPREGION_TOR          ((((     PMP_R|PMP_W|PMP_X |PMP_TOR)   &0xFF) << PMP0_CFG_SHIFT))

#define PMPADDRESS_TOP_GLOBAL        -1                                                // All memory region
#define REGIONSTART            0x80002000        // RAM_BASE_ADDR + PROGRAM_SIZE
#define PMP_ADDRESS            (REGIONSTART >> PMP_SHIFT)
#define CHECKERBOARD        0xAAAAAAAAAAAAAAAA


    LA(x4, PMPADDRESS_TOP_GLOBAL)
    csrw     pmpaddr15, x4

    //Lock the Background region
    LI(x4, PMP_REGION_GLOBAL)
    csrw pmpcfg2, x4

    LA(x4, PMP_ADDRESS)
    csrw     pmpaddr0, x4
                                                //Verification Section
    // Test Case 1: Writing all 0s in pmpaddr0 when A = NAPOT and read back when A= {OFF,NAPOT,TOR}

    // Write all 0s in NAPOT
    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    li x6, 0
    csrw pmpaddr0, x6

    // Read back in OFF
    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    tc_1:
    csrr x7, pmpaddr0
    RVTEST_SIGUPD(x2, x5, x4, x7, tc_1, test_1_str)

    // Test Case 2: Writing all 0s in pmpaddr0 when A = NAPOT and read back in NAPOT

    // Write all 0s in NAPOT
    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    li x6, 0
    csrw pmpaddr0, x6

    // Read back in NAPOT
    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    tc_2:
    csrr x7, pmpaddr0
    RVTEST_SIGUPD(x2, x5, x4, x7, tc_2, test_2_str)

    // Test Case 3: Writing all 0s in pmpaddr0 when A = NAPOT and read back in TOR

    // Write all 0s in NAPOT
    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    li x6, 0
    csrw pmpaddr0, x6

    // Read back in TOR
    LI(x6, PMPREGION_TOR)
    csrw pmpcfg0, x6
    tc_3:
    csrr x7, pmpaddr0
    RVTEST_SIGUPD(x2, x5, x4, x7, tc_3, test_3_str)

    // Test Case 4: Writing all 0s in pmpaddr0 when A = OFF and read back in OFF

    // Write all 0s in OFF
    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    li x6, 0
    csrw pmpaddr0, x6

    // Read back in OFF
    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    tc_4:
    csrr x7, pmpaddr0
    RVTEST_SIGUPD(x2, x5, x4, x7, tc_4, test_4_str)

    // Test Case 5: Writing all 0s in pmpaddr0 when A = OFF and read back in NAPOT

    // Write all 0s in OFF
    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    li x6, 0
    csrw pmpaddr0, x6

    // Read back in NAPOT
    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    tc_5:
    csrr x7, pmpaddr0
    RVTEST_SIGUPD(x2, x5, x4, x7, tc_5, test_5_str)

    // Test Case 6: Writing all 0s in pmpaddr0 when A = OFF and read back in TOR

    // Write all 0s in OFF
    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    li x6, 0
    csrw pmpaddr0, x6

    // Read back in TOR
    LI(x6, PMPREGION_TOR)
    csrw pmpcfg0, x6
    tc_6:
    csrr x7, pmpaddr0
    RVTEST_SIGUPD(x2, x5, x4, x7, tc_6, test_6_str)

    // Test Case 7: Writing all 1s in pmpaddr0 when A = NAPOT and read back in OFF

    // Write all 1s in NAPOT
    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    li x6, -1
    csrw pmpaddr0, x6

    // Read back in OFF
    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    tc_7:
    csrr x7, pmpaddr0
    RVTEST_SIGUPD(x2, x5, x4, x7, tc_7, test_7_str)

    // Test Case 8: Writing all 1s in pmpaddr0 when A = NAPOT and read back in NAPOT

    // Write all 1s in NAPOT
    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    li x6, -1
    csrw pmpaddr0, x6

    // Read back in NAPOT
    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    tc_8:
    csrr x7, pmpaddr0
    RVTEST_SIGUPD(x2, x5, x4, x7, tc_8, test_8_str)

    // Test Case 9: Writing all 1s in pmpaddr0 when A = NAPOT and read back in TOR

    // Write all 1s in NAPOT
    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    li x6, -1
    csrw pmpaddr0, x6

    // Read back in TOR
    LI(x6, PMPREGION_TOR)
    csrw pmpcfg0, x6
    tc_9:
    csrr x7, pmpaddr0
    RVTEST_SIGUPD(x2, x5, x4, x7, tc_9, test_9_str)

    // Test Case 10: Writing all 1s in pmpaddr0 when A = OFF and read back in OFF

    // Write all 1s in OFF
    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    li x6, -1
    csrw pmpaddr0, x6

    // Read back in OFF
    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    tc_10:
    csrr x7, pmpaddr0
    RVTEST_SIGUPD(x2, x5, x4, x7, tc_10, test_10_str)

    // Test Case 11: Writing all 1s in pmpaddr0 when A = OFF and read back in NAPOT

    // Write all 1s in OFF
    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    li x6, -1
    csrw pmpaddr0, x6

    // Read back in NAPOT
    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    tc_11:
    csrr x7, pmpaddr0
    RVTEST_SIGUPD(x2, x5, x4, x7, tc_11, test_11_str)

    // Test Case 12: Writing all 1s in pmpaddr0 when A = OFF and read back in TOR

    // Write all 1s in OFF
    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    li x6, -1
    csrw pmpaddr0, x6

    // Read back in TOR
    LI(x6, PMPREGION_TOR)
    csrw pmpcfg0, x6
    tc_12:
    csrr x7, pmpaddr0
    RVTEST_SIGUPD(x2, x5, x4, x7, tc_12, test_12_str)

    // Test Case 13: Writing checkerboard in pmpaddr0 when A = NAPOT and read back in OFF

    // Write checkerboard in NAPOT
    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    LI(x6, CHECKERBOARD)
    csrw pmpaddr0, x6

    // Read back in OFF
    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    tc_13:
    csrr x7, pmpaddr0
    RVTEST_SIGUPD(x2, x5, x4, x7, tc_13, test_13_str)

    // Test Case 14: Writing checkerboard in pmpaddr0 when A = NAPOT and read back in NAPOT

    // Write checkerboard in NAPOT
    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    LI(x6, CHECKERBOARD)
    csrw pmpaddr0, x6

    // Read back in NAPOT
    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    tc_14:
    csrr x7, pmpaddr0
    RVTEST_SIGUPD(x2, x5, x4, x7, tc_14, test_14_str)

    // Test Case 15: Writing checkerboard in pmpaddr0 when A = NAPOT and read back in TOR

    // Write checkerboard in NAPOT
    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    LI(x6, CHECKERBOARD)
    csrw pmpaddr0, x6

    // Read back in TOR
    LI(x6, PMPREGION_TOR)
    csrw pmpcfg0, x6
    tc_15:
    csrr x7, pmpaddr0
    RVTEST_SIGUPD(x2, x5, x4, x7, tc_15, test_15_str)

    // Test Case 16: Writing checkerboard in pmpaddr0 when A = OFF and read back in OFF

    // Write checkerboard in OFF
    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    LI(x6, CHECKERBOARD)
    csrw pmpaddr0, x6

    // Read back in OFF
    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    tc_16:
    csrr x7, pmpaddr0
    RVTEST_SIGUPD(x2, x5, x4, x7, tc_16, test_16_str)

    // Test Case 17: Writing checkerboard in pmpaddr0 when A = OFF and read back in NAPOT

    // Write checkerboard in OFF
    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    LI(x6, CHECKERBOARD)
    csrw pmpaddr0, x6

    // Read back in NAPOT
    LI(x6, PMPREGION_NAPOT)
    csrw pmpcfg0, x6
    tc_17:
    csrr x7, pmpaddr0
    RVTEST_SIGUPD(x2, x5, x4, x7, tc_17, test_17_str)

    // Test Case 18: Writing checkerboard in pmpaddr0 when A = OFF and read back in TOR

    // Write checkerboard in OFF
    LI(x6, PMPREGION_OFF)
    csrw pmpcfg0, x6
    LI(x6, CHECKERBOARD)
    csrw pmpaddr0, x6

    // Read back in TOR
    LI(x6, PMPREGION_TOR)
    csrw pmpcfg0, x6
    tc_18:
    csrr x7, pmpaddr0
    RVTEST_SIGUPD(x2, x5, x4, x7, tc_18, test_18_str)

    RVTEST_GOTO_MMODE
    j exit                                                        // Verification Complete, exit the test

.align 13
.align (RVMODEL_PMP_GRAIN+2)
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
test_1_str:  .string "\"test: 1;  cp: cp_pmp_grain\""
test_2_str:  .string "\"test: 2;  cp: cp_pmp_grain\""
test_3_str:  .string "\"test: 3;  cp: cp_pmp_grain\""
test_4_str:  .string "\"test: 4;  cp: cp_pmp_grain\""
test_5_str:  .string "\"test: 5;  cp: cp_pmp_grain\""
test_6_str:  .string "\"test: 6;  cp: cp_pmp_grain\""
test_7_str:  .string "\"test: 7;  cp: cp_pmp_grain\""
test_8_str:  .string "\"test: 8;  cp: cp_pmp_grain\""
test_9_str:  .string "\"test: 9;  cp: cp_pmp_grain\""
test_10_str: .string "\"test: 10; cp: cp_pmp_grain\""
test_11_str: .string "\"test: 11; cp: cp_pmp_grain\""
test_12_str: .string "\"test: 12; cp: cp_pmp_grain\""
test_13_str: .string "\"test: 13; cp: cp_pmp_grain\""
test_14_str: .string "\"test: 14; cp: cp_pmp_grain\""
test_15_str: .string "\"test: 15; cp: cp_pmp_grain\""
test_16_str: .string "\"test: 16; cp: cp_pmp_grain\""
test_17_str: .string "\"test: 17; cp: cp_pmp_grain\""
test_18_str: .string "\"test: 18; cp: cp_pmp_grain\""

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
