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
// Coverpoints : cp_cfg_A_all for PMPM is fully covered in this test file.
//
// Test Cases  : Checking that A is writable in each region. For each standard
//               region, attempt to write pmpcfg.A={OFF, TOR, NA4, NAPOT} with
//               pmpcfg.L=0, pmpcfg.RWX = 000.  Only able to write NA4 if grain
//               G = 0. Other pmpcfg bits are writable.
// --------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS:  ['I','Smpmp']
# params:
#   MXLEN: 32
# MARCH: rv32i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpsm_cfg_A_all.S"
#define SIGUPD_COUNT 100

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

#define PMP_REGION_GLOBAL   ((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF)  // Background region with RWX enable.
#define PMPADDRESS_TOP_GLOBAL       -1                                              // All memory region
#define NAPOT   (PMP_NAPOT & 0xFF)
#define TOR     (PMP_TOR   & 0xFF)
#define NA4     (PMP_NA4   & 0xFF)

    LA(x4, PMPADDRESS_TOP_GLOBAL)
    csrw    pmpaddr15, x4

    //Lock the Background region.
    LI(x4, (PMP_REGION_GLOBAL << PMP3_CFG_SHIFT))
    csrw pmpcfg3, x4

//                                          Verification Section
// Test Case 1 : Setting region 0-14 to be NA4, NAPOT, TOR and OFF with L->0, XWR->000

    LI(x4, (NA4 << PMP3_CFG_SHIFT|NA4 << PMP2_CFG_SHIFT|NA4 << PMP1_CFG_SHIFT|NA4 << PMP0_CFG_SHIFT))

    test_1:
    # Write x4 to pmpcfg0, read back and check against expected.
    RVTEST_SIGUPD_CSR_WRITE(pmpcfg0, x4, test_1, test_1_str)

    test_2:
    # Write x4 to pmpcfg1, read back and check against expected.
    RVTEST_SIGUPD_CSR_WRITE(pmpcfg1, x4, test_2, test_2_str)

    test_3:
    # Write x4 to pmpcfg2, read back and check against expected.
    RVTEST_SIGUPD_CSR_WRITE(pmpcfg2, x4, test_3, test_3_str)

    test_4:
    # Write x4 to pmpcfg3, read back and check against expected.
    RVTEST_SIGUPD_CSR_WRITE(pmpcfg3, x4, test_4, test_4_str)

.if RVMODEL_NUM_PMPS == 64
   test_5:
       # Write x4 to pmpcfg4, read back and check against expected.
       RVTEST_SIGUPD_CSR_WRITE(pmpcfg4, x4, test_5, test_5_str)

   test_6:
       # Write x4 to pmpcfg5, read back and check against expected.
       RVTEST_SIGUPD_CSR_WRITE(pmpcfg5, x4, test_6, test_6_str)

   test_7:
       # Write x4 to pmpcfg6, read back and check against expected.
       RVTEST_SIGUPD_CSR_WRITE(pmpcfg6, x4, test_7, test_7_str)

   test_8:
       # Write x4 to pmpcfg7, read back and check against expected.
       RVTEST_SIGUPD_CSR_WRITE(pmpcfg7, x4, test_8, test_8_str)

   test_9:
       # Write x4 to pmpcfg8, read back and check against expected.
       RVTEST_SIGUPD_CSR_WRITE(pmpcfg8, x4, test_9, test_9_str)

   test_10:
       # Write x4 to pmpcfg9, read back and check against expected.
       RVTEST_SIGUPD_CSR_WRITE(pmpcfg9, x4, test_10, test_10_str)

   test_11:
       # Write x4 to pmpcfg10, read back and check against expected.
       RVTEST_SIGUPD_CSR_WRITE(pmpcfg10, x4, test_11, test_11_str)

   test_12:
       # Write x4 to pmpcfg11, read back and check against expected.
       RVTEST_SIGUPD_CSR_WRITE(pmpcfg11, x4, test_12, test_12_str)

   test_13:
       # Write x4 to pmpcfg12, read back and check against expected.
       RVTEST_SIGUPD_CSR_WRITE(pmpcfg12, x4, test_13, test_13_str)

   test_14:
       # Write x4 to pmpcfg13, read back and check against expected.
       RVTEST_SIGUPD_CSR_WRITE(pmpcfg13, x4, test_14, test_14_str)

   test_15:
       # Write x4 to pmpcfg14, read back and check against expected.
       RVTEST_SIGUPD_CSR_WRITE(pmpcfg14, x4, test_15, test_15_str)

   test_16:
       # Write x4 to pmpcfg15, read back and check against expected.
       RVTEST_SIGUPD_CSR_WRITE(pmpcfg15, x4, test_16, test_16_str)
.endif

    LI(x4, (NAPOT << PMP3_CFG_SHIFT|NAPOT << PMP2_CFG_SHIFT|NAPOT << PMP1_CFG_SHIFT|NAPOT << PMP0_CFG_SHIFT))
    test_17:
    # Write x4 to pmpcfg0, read back and check against expected.
    RVTEST_SIGUPD_CSR_WRITE(pmpcfg0, x4, test_17, test_17_str)

    test_18:
    # Write x4 to pmpcfg1, read back and check against expected.
    RVTEST_SIGUPD_CSR_WRITE(pmpcfg1, x4, test_18, test_18_str)

    test_19:
    # Write x4 to pmpcfg2, read back and check against expected.
    RVTEST_SIGUPD_CSR_WRITE(pmpcfg2, x4, test_19, test_19_str)

    test_20:
    # Write x4 to pmpcfg3, read back and check against expected.
    RVTEST_SIGUPD_CSR_WRITE(pmpcfg3, x4, test_20, test_20_str)

.if RVMODEL_NUM_PMPS == 64
    test_21:
        # Write x4 to pmpcfg4, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg4, x4, test_21, test_21_str)

    test_22:
        # Write x4 to pmpcfg5, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg5, x4, test_22, test_22_str)

    test_23:
        # Write x4 to pmpcfg6, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg6, x4, test_23, test_23_str)

    test_24:
        # Write x4 to pmpcfg7, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg7, x4, test_24, test_24_str)

    test_25:
        # Write x4 to pmpcfg8, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg8, x4, test_25, test_25_str)

    test_26:
        # Write x4 to pmpcfg9, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg9, x4, test_26, test_26_str)

    test_27:
        # Write x4 to pmpcfg10, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg10, x4, test_27, test_27_str)

    test_28:
        # Write x4 to pmpcfg11, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg11, x4, test_28, test_28_str)

    test_29:
        # Write x4 to pmpcfg12, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg12, x4, test_29, test_29_str)

    test_30:
        # Write x4 to pmpcfg13, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg13, x4, test_30, test_30_str)

    test_31:
        # Write x4 to pmpcfg14, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg14, x4, test_31, test_31_str)

    test_32:
        # Write x4 to pmpcfg15, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg15, x4, test_32, test_32_str)
.endif

    LI(x4, (TOR << PMP3_CFG_SHIFT|TOR << PMP2_CFG_SHIFT|TOR << PMP1_CFG_SHIFT|TOR << PMP0_CFG_SHIFT))
    test_33:
        # Write x4 to pmpcfg0, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg0, x4, test_33, test_33_str)

    test_34:
        # Write x4 to pmpcfg1, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg1, x4, test_34, test_34_str)

    test_35:
        # Write x4 to pmpcfg2, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg2, x4, test_35, test_35_str)

    test_36:
        # Write x4 to pmpcfg3, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg3, x4, test_36, test_36_str)

.if RVMODEL_NUM_PMPS == 64
    test_37:
        # Write x4 to pmpcfg4, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg4, x4, test_37, test_37_str)

    test_38:
        # Write x4 to pmpcfg5, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg5, x4, test_38, test_38_str)

    test_39:
        # Write x4 to pmpcfg6, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg6, x4, test_39, test_39_str)

    test_40:
        # Write x4 to pmpcfg7, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg7, x4, test_40, test_40_str)

    test_41:
        # Write x4 to pmpcfg8, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg8, x4, test_41, test_41_str)

    test_42:
        # Write x4 to pmpcfg9, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg9, x4, test_42, test_42_str)

    test_43:
        # Write x4 to pmpcfg10, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg10, x4, test_43, test_43_str)

    test_44:
        # Write x4 to pmpcfg11, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg11, x4, test_44, test_44_str)

    test_45:
        # Write x4 to pmpcfg12, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg12, x4, test_45, test_45_str)

    test_46:
        # Write x4 to pmpcfg13, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg13, x4, test_46, test_46_str)

    test_47:
        # Write x4 to pmpcfg14, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg14, x4, test_47, test_47_str)

    test_48:
        # Write x4 to pmpcfg15, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg15, x4, test_48, test_48_str)
.endif

    test_49:
        # Write zero to pmpcfg0, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg0, zero, test_49, test_49_str)

    test_50:
        # Write zero to pmpcfg1, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg1, zero, test_50, test_50_str)

    test_51:
        # Write zero to pmpcfg2, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg2, zero, test_51, test_51_str)

    test_52:
        # Write zero to pmpcfg3, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg3, zero, test_52, test_52_str)

.if RVMODEL_NUM_PMPS == 64
    test_53:
        # Write zero to pmpcfg4, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg4, zero, test_53, test_53_str)

    test_54:
        # Write zero to pmpcfg5, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg5, zero, test_54, test_54_str)

    test_55:
        # Write zero to pmpcfg6, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg6, zero, test_55, test_55_str)

    test_56:
        # Write zero to pmpcfg7, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg7, zero, test_56, test_56_str)

    test_57:
        # Write zero to pmpcfg8, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg8, zero, test_57, test_57_str)

    test_58:
        # Write zero to pmpcfg9, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg9, zero, test_58, test_58_str)

    test_59:
        # Write zero to pmpcfg10, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg10, zero, test_59, test_59_str)

    test_60:
        # Write zero to pmpcfg11, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg11, zero, test_60, test_60_str)

    test_61:
        # Write zero to pmpcfg12, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg12, zero, test_61, test_61_str)

    test_62:
        # Write zero to pmpcfg13, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg13, zero, test_62, test_62_str)

    test_63:
        # Write zero to pmpcfg14, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg14, zero, test_63, test_63_str)

    test_64:
        # Write zero to pmpcfg15, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg15, zero, test_64, test_64_str)
.endif

// ---------------------------------------------------------------------------

    j exit                                                      // Verification Complete, exit the test

.align 12
.align (RVMODEL_PMP_GRAIN+2)

RETURN_INSTRUCTION:
    nop
    nop
    jr ra                                                       // Get back to the point from where TEST_FOR_EXECUTION was called.

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
test_33_str: .string "\"test: 33; cp: cp_cfg_A_all_test_33\""
test_34_str: .string "\"test: 34; cp: cp_cfg_A_all_test_34\""
test_35_str: .string "\"test: 35; cp: cp_cfg_A_all_test_35\""
test_36_str: .string "\"test: 36; cp: cp_cfg_A_all_test_36\""
test_37_str: .string "\"test: 37; cp: cp_cfg_A_all_test_37\""
test_38_str: .string "\"test: 38; cp: cp_cfg_A_all_test_38\""
test_39_str: .string "\"test: 39; cp: cp_cfg_A_all_test_39\""
test_40_str: .string "\"test: 40; cp: cp_cfg_A_all_test_40\""
test_41_str: .string "\"test: 41; cp: cp_cfg_A_all_test_41\""
test_42_str: .string "\"test: 42; cp: cp_cfg_A_all_test_42\""
test_43_str: .string "\"test: 43; cp: cp_cfg_A_all_test_43\""
test_44_str: .string "\"test: 44; cp: cp_cfg_A_all_test_44\""
test_45_str: .string "\"test: 45; cp: cp_cfg_A_all_test_45\""
test_46_str: .string "\"test: 46; cp: cp_cfg_A_all_test_46\""
test_47_str: .string "\"test: 47; cp: cp_cfg_A_all_test_47\""
test_48_str: .string "\"test: 48; cp: cp_cfg_A_all_test_48\""
test_49_str: .string "\"test: 49; cp: cp_cfg_A_all_test_49\""
test_50_str: .string "\"test: 50; cp: cp_cfg_A_all_test_50\""
test_51_str: .string "\"test: 51; cp: cp_cfg_A_all_test_51\""
test_52_str: .string "\"test: 52; cp: cp_cfg_A_all_test_52\""
test_53_str: .string "\"test: 53; cp: cp_cfg_A_all_test_53\""
test_54_str: .string "\"test: 54; cp: cp_cfg_A_all_test_54\""
test_55_str: .string "\"test: 55; cp: cp_cfg_A_all_test_55\""
test_56_str: .string "\"test: 56; cp: cp_cfg_A_all_test_56\""
test_57_str: .string "\"test: 57; cp: cp_cfg_A_all_test_57\""
test_58_str: .string "\"test: 58; cp: cp_cfg_A_all_test_58\""
test_59_str: .string "\"test: 59; cp: cp_cfg_A_all_test_59\""
test_60_str: .string "\"test: 60; cp: cp_cfg_A_all_test_60\""
test_61_str: .string "\"test: 61; cp: cp_cfg_A_all_test_61\""
test_62_str: .string "\"test: 62; cp: cp_cfg_A_all_test_62\""
test_63_str: .string "\"test: 63; cp: cp_cfg_A_all_test_63\""
test_64_str: .string "\"test: 64; cp: cp_cfg_A_all_test_64\""

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
