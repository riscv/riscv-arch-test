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
# REQUIRED_EXTENSIONS:  ['I','Smpmp']
# params:
#   MXLEN: 32
# MARCH: rv32i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpsm_csr_walk.S"
#define SIGUPD_COUNT 250

// Enable trap handler
#define rvtest_mtrap_routine
#define RVTEST_PRIV_TEST

// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

main:
    RVTEST_GOTO_MMODE

    // Loop to SET ALL pmpaddr REGs to zeros
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
    csrw pmpaddri, x0
    .set pmpaddri, pmpaddri+1
    .endr

    li t0, -1
    // Loop to SET ALL pmpaddr REGs to ones
    .set pmpaddri, CSR_PMPADDR0
    .rept RVMODEL_NUM_PMPS
    csrw pmpaddri, t0
    .set pmpaddri, pmpaddri+1
    .endr

    // Loop to SET ALL pmpcfg REGs to zero
    .set pmpcfgi, CSR_PMPCFG0
    .rept RVMODEL_NUM_PMPS/4
    csrw pmpcfgi , x0
    .set pmpcfgi, pmpcfgi+1
    .endr


    li t2, 1                     // walking one: 0x00000001

9:  // Outer loop for walking ones
    test_1:
    # Write t2 to pmpaddr0, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpaddr0, t2, test_1, test_1_str)
    test_2:
    # Write t2 to pmpaddr1, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpaddr1, t2, test_2, test_2_str)
    test_3:
    # Write t2 to pmpaddr2, read back and check against expected.
        RVTEST_SIGUPD_CSR_WRITE(pmpaddr2, t2, test_3, test_3_str)
    test_4:
        RVTEST_SIGUPD_CSR_WRITE(pmpaddr3, t2, test_4, test_4_str)
    test_5:
        RVTEST_SIGUPD_CSR_WRITE(pmpaddr4, t2, test_5, test_5_str)
    test_6:
        RVTEST_SIGUPD_CSR_WRITE(pmpaddr5, t2, test_6, test_6_str)
    test_7:
        RVTEST_SIGUPD_CSR_WRITE(pmpaddr6, t2, test_7, test_7_str)
    test_8:
        RVTEST_SIGUPD_CSR_WRITE(pmpaddr7, t2, test_8, test_8_str)
    test_9:
        RVTEST_SIGUPD_CSR_WRITE(pmpaddr8, t2, test_9, test_9_str)
    test_10:
        RVTEST_SIGUPD_CSR_WRITE(pmpaddr9, t2, test_10, test_10_str)
    test_11:
        RVTEST_SIGUPD_CSR_WRITE(pmpaddr10, t2, test_11, test_11_str)
    test_12:
        RVTEST_SIGUPD_CSR_WRITE(pmpaddr11, t2, test_12, test_12_str)
    test_13:
        RVTEST_SIGUPD_CSR_WRITE(pmpaddr12, t2, test_13, test_13_str)
    test_14:
        RVTEST_SIGUPD_CSR_WRITE(pmpaddr13, t2, test_14, test_14_str)
    test_15:
        RVTEST_SIGUPD_CSR_WRITE(pmpaddr14, t2, test_15, test_15_str)
    test_16:
        RVTEST_SIGUPD_CSR_WRITE(pmpaddr15, t2, test_16, test_16_str)

    .if RVMODEL_NUM_PMPS == 64
        test_17:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr16, t2, test_17, test_17_str)
        test_18:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr17, t2, test_18, test_18_str)
        test_19:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr18, t2, test_19, test_19_str)
        test_20:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr19, t2, test_20, test_20_str)
        test_21:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr20, t2, test_21, test_21_str)
        test_22:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr21, t2, test_22, test_22_str)
        test_23:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr22, t2, test_23, test_23_str)
        test_24:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr23, t2, test_24, test_24_str)
        test_25:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr24, t2, test_25, test_25_str)
        test_26:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr25, t2, test_26, test_26_str)
        test_27:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr26, t2, test_27, test_27_str)
        test_28:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr27, t2, test_28, test_28_str)
        test_29:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr28, t2, test_29, test_29_str)
        test_30:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr29, t2, test_30, test_30_str)
        test_31:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr30, t2, test_31, test_31_str)
        test_32:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr31, t2, test_32, test_32_str)
        test_33:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr32, t2, test_33, test_33_str)
        test_34:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr33, t2, test_34, test_34_str)
        test_35:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr34, t2, test_35, test_35_str)
        test_36:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr35, t2, test_36, test_36_str)
        test_37:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr36, t2, test_37, test_37_str)
        test_38:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr37, t2, test_38, test_38_str)
        test_39:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr38, t2, test_39, test_39_str)
        test_40:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr39, t2, test_40, test_40_str)
        test_41:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr40, t2, test_41, test_41_str)
        test_42:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr41, t2, test_42, test_42_str)
        test_43:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr42, t2, test_43, test_43_str)
        test_44:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr43, t2, test_44, test_44_str)
        test_45:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr44, t2, test_45, test_45_str)
        test_46:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr45, t2, test_46, test_46_str)
        test_47:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr46, t2, test_47, test_47_str)
        test_48:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr47, t2, test_48, test_48_str)
        test_49:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr48, t2, test_49, test_49_str)
        test_50:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr49, t2, test_50, test_50_str)
        test_51:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr50, t2, test_51, test_51_str)
        test_52:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr51, t2, test_52, test_52_str)
        test_53:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr52, t2, test_53, test_53_str)
        test_54:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr53, t2, test_54, test_54_str)
        test_55:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr54, t2, test_55, test_55_str)
        test_56:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr55, t2, test_56, test_56_str)
        test_57:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr56, t2, test_57, test_57_str)
        test_58:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr57, t2, test_58, test_58_str)
        test_59:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr58, t2, test_59, test_59_str)
        test_60:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr59, t2, test_60, test_60_str)
        test_61:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr60, t2, test_61, test_61_str)
        test_62:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr61, t2, test_62, test_62_str)
        test_63:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr62, t2, test_63, test_63_str)
        test_64:
                RVTEST_SIGUPD_CSR_WRITE(pmpaddr63, t2, test_64, test_64_str)
    .endif

    slli t2, t2, 1
    bnez t2, 9b

    li t2, 1

8:  // Outer loop for walking ones

    // Skip reserved encoding: any region where R=0 and W=1
    // That happens only when walking bit hits any (8*i + 1)

    li t3, 0x02020202  // all W-bit positions in 64-bit pmpcfg
    and  t4, t2, t3
    bnez t4, skip_write

    test_65:
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg0, t2, test_65, test_65_str)
    test_66:
        RVTEST_SIGUPD_CSR_WRITE(pmpcfg2, t2, test_66, test_66_str)

    .if RVMODEL_NUM_PMPS == 64
        test_67:
                RVTEST_SIGUPD_CSR_WRITE(pmpcfg4, t2, test_67, test_67_str)
        test_68:
                RVTEST_SIGUPD_CSR_WRITE(pmpcfg6, t2, test_68, test_68_str)
        test_69:
                RVTEST_SIGUPD_CSR_WRITE(pmpcfg8, t2, test_69, test_69_str)
        test_70:
                RVTEST_SIGUPD_CSR_WRITE(pmpcfg10, t2, test_70, test_70_str)
        test_71:
                RVTEST_SIGUPD_CSR_WRITE(pmpcfg12, t2, test_71, test_71_str)
        test_72:
                RVTEST_SIGUPD_CSR_WRITE(pmpcfg14, t2, test_72, test_72_str)
    .endif

skip_write:
    slli t2, t2, 1
    bnez t2, 8b

    RVTEST_GOTO_MMODE
    j exit                                      // Verification Complete, exit the test

.align 10
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
