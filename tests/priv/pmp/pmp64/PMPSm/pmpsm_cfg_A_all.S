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
// Coverpoints : cp_cfg_A_all for PMPM is fully covered in this test file.
//
// Test Cases  : Checking that A is writable in each region. For each standard
//               region, attempt to write pmpcfg.A={OFF, TOR, NA4, NAPOT} with
//               pmpcfg.L=0, pmpcfg.RWX = 000.  Only able to write NA4 if grain
//                G = 0. Other pmpcfg bits are writable.
//
// --------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['I','Smpmp']
# params:
#   MXLEN: 64
# MARCH: rv64i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpsm_cfg_A_all.S"
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
    .rept RVMODEL_NUM_PMPS/8
    csrw pmpcfgi , x0
    .set pmpcfgi, pmpcfgi+2
    .endr

#define PMP_REGION_GLOBAL    ((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF)  // Background region with RWX enable.
#define PMPADDRESS_TOP_GLOBAL        -1                                                // All memory region
#define NAPOT   (PMP_NAPOT & 0xFF)
#define TOR     (PMP_TOR   & 0xFF)
#define NA4     (PMP_NA4   & 0xFF)

    LA(x4, PMPADDRESS_TOP_GLOBAL)
    csrw     pmpaddr15, x4

    //Lock the Background region.
    LI(x4, (PMP_REGION_GLOBAL << PMP7_CFG_SHIFT))
    csrw pmpcfg2, x4

//                                            Verification Section
// Test Case 1 : Setting region 0-14 to be NA4, NAPOT, TOR and OFF with L->0, XWR->000

    LI(x4, (NA4   << PMP7_CFG_SHIFT|NA4   << PMP6_CFG_SHIFT|NA4   << PMP5_CFG_SHIFT|NA4   << PMP4_CFG_SHIFT|NA4   << PMP3_CFG_SHIFT|NA4   << PMP2_CFG_SHIFT|NA4   << PMP1_CFG_SHIFT|NA4  ))
    test_1:
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg0, x4, test_1, test_1_str)
    test_2:
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg2, x4, test_2, test_2_str)

.if RVMODEL_NUM_PMPS == 64
    test_3:
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg4, x4, test_3, test_3_str)
    test_4:
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg6, x4, test_4, test_4_str)
    test_5:
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg8, x4, test_5, test_5_str)
    test_6:
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg10, x4, test_6, test_6_str)
    test_7:
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg12, x4, test_7, test_7_str)
    test_8:
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg14, x4, test_8, test_8_str)
.endif

    LI(x4, (NAPOT << PMP7_CFG_SHIFT|NAPOT << PMP6_CFG_SHIFT|NAPOT << PMP5_CFG_SHIFT|NAPOT << PMP4_CFG_SHIFT|NAPOT << PMP3_CFG_SHIFT|NAPOT << PMP2_CFG_SHIFT|NAPOT << PMP1_CFG_SHIFT|NAPOT))
    test_9:
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg0, x4, test_9, test_9_str)
    test_10:
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg2, x4, test_10, test_10_str)

.if RVMODEL_NUM_PMPS == 64
    test_11:
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg4, x4, test_11, test_11_str)
    test_12:
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg6, x4, test_12, test_12_str)
    test_13:
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg8, x4, test_13, test_13_str)
    test_14:
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg10, x4, test_14, test_14_str)
    test_15:
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg12, x4, test_15, test_15_str)
    test_16:
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg14, x4, test_16, test_16_str)
.endif

    LI(x4, (TOR   << PMP7_CFG_SHIFT|TOR   << PMP6_CFG_SHIFT|TOR   << PMP5_CFG_SHIFT|TOR    << PMP4_CFG_SHIFT|TOR   << PMP3_CFG_SHIFT|TOR   << PMP2_CFG_SHIFT|TOR  << PMP1_CFG_SHIFT|TOR  ))
    test_17:
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg0, x4, test_17, test_17_str)
    test_18:
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg2, x4, test_18, test_18_str)

.if RVMODEL_NUM_PMPS == 64
    test_19:
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg4, x4, test_19, test_19_str)
    test_20:
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg6, x4, test_20, test_20_str)
    test_21:
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg8, x4, test_21, test_21_str)
    test_22:
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg10, x4, test_22, test_22_str)
    test_23:
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg12, x4, test_23, test_23_str)
    test_24:
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg14, x4, test_24, test_24_str)
.endif

   test_25:
       RVTEST_SIGUPD_CSR_WRITE(pmpcfg0, zero, test_25, test_25_str)
   test_26:
       RVTEST_SIGUPD_CSR_WRITE(pmpcfg2, zero, test_26, test_26_str)

.if RVMODEL_NUM_PMPS == 64
    test_27:
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg4, zero, test_27, test_27_str)
    test_28:
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg6, zero, test_28, test_28_str)
    test_29:
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg8, zero, test_29, test_29_str)
    test_30:
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg10, zero, test_30, test_30_str)
    test_31:
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg12, zero, test_31, test_31_str)
    test_32:
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg14, zero, test_32, test_32_str)
.endif

// ---------------------------------------------------------------------------

    j exit                                                        // Verification Complete, exit the test

.align 12
.align (RVMODEL_PMP_GRAIN+2)

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
test_1_str:  .string "\"test: 1; cp: cp_cfg_A_all_test_1\""
test_2_str:  .string "\"test: 2; cp: cp_cfg_A_all_test_2\""
test_3_str:  .string "\"test: 3; cp: cp_cfg_A_all_test_3\""
test_4_str:  .string "\"test: 4; cp: cp_cfg_A_all_test_4\""
test_5_str:  .string "\"test: 5; cp: cp_cfg_A_all_test_5\""
test_6_str:  .string "\"test: 6; cp: cp_cfg_A_all_test_6\""
test_7_str:  .string "\"test: 7; cp: cp_cfg_A_all_test_7\""
test_8_str:  .string "\"test: 8; cp: cp_cfg_A_all_test_8\""
test_9_str:  .string "\"test: 9; cp: cp_cfg_A_all_test_9\""
test_10_str: .string "\"test: 10; cp: cp_cfg_A_all_test_10\""
test_11_str: .string "\"test: 11; cp: cp_cfg_A_all_test_11\""
test_12_str: .string "\"test: 12; cp: cp_cfg_A_all_test_12\""
test_13_str: .string "\"test: 13; cp: cp_cfg_A_all_test_13\""
test_14_str: .string "\"test: 14; cp: cp_cfg_A_all_test_14\""
test_15_str: .string "\"test: 15; cp: cp_cfg_A_all_test_15\""
test_16_str: .string "\"test: 16; cp: cp_cfg_A_all_test_16\""
test_17_str: .string "\"test: 17; cp: cp_cfg_A_all_test_17\""
test_18_str: .string "\"test: 18; cp: cp_cfg_A_all_test_18\""
test_19_str: .string "\"test: 19; cp: cp_cfg_A_all_test_19\""
test_20_str: .string "\"test: 20; cp: cp_cfg_A_all_test_20\""
test_21_str: .string "\"test: 21; cp: cp_cfg_A_all_test_21\""
test_22_str: .string "\"test: 22; cp: cp_cfg_A_all_test_22\""
test_23_str: .string "\"test: 23; cp: cp_cfg_A_all_test_23\""
test_24_str: .string "\"test: 24; cp: cp_cfg_A_all_test_24\""
test_25_str: .string "\"test: 25; cp: cp_cfg_A_all_test_25\""
test_26_str: .string "\"test: 26; cp: cp_cfg_A_all_test_26\""
test_27_str: .string "\"test: 27; cp: cp_cfg_A_all_test_27\""
test_28_str: .string "\"test: 28; cp: cp_cfg_A_all_test_28\""
test_29_str: .string "\"test: 29; cp: cp_cfg_A_all_test_29\""
test_30_str: .string "\"test: 30; cp: cp_cfg_A_all_test_30\""
test_31_str: .string "\"test: 31; cp: cp_cfg_A_all_test_31\""
test_32_str: .string "\"test: 32; cp: cp_cfg_A_all_test_32\""

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
