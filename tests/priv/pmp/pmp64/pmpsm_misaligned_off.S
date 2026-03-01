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
// Coverpoints :  cp_misaligned_off for PMPM is fully covered in this test file.
//
// Test Cases  :  Checking that misaligned read/write that crosses a  PMP boundary
//                with A=OFF does not fail. We Set up standard OFF region with
//                L={0/1}, XWR = 111 and attempt misaligned {lw, lh, lhu, sw, sh}
//                stradding each offset partially in start and end of region.
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
#define TEST_FILE "pmpsm_mislaigned_off.S"
#define SIGUPD_COUNT 50

// Enable trap handler
#define rvtest_mtrap_routine
#define RVTEST_PRIV_TEST

// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

#define g       (1<<(RVMODEL_PMP_GRAIN+2))

.macro VERIFICATION_RWX ADDRESS TEST_CASE

    LI(a4, NOP32)                                      // Value to write (NOP)

    // Access Check straddling start
    LA(a5, (\ADDRESS-1))

    \TEST_CASE\()_1:
    sh a4, 0(a5)                                             // Half-word store test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_1, test_1_str)

    \TEST_CASE\()_2:
    lh a4, 0(a5)                                             // Half-word load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_2, test_2_str)

    \TEST_CASE\()_3:
    lhu a4, 0(a5)                                            // Half-word load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_3, test_3_str)


    LI(a4, NOP32)

    \TEST_CASE\()_4:
    sw a4, 0(a5)                                             // Word-level store test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_4, test_4_str)

    \TEST_CASE\()_5:
    lw a4, 0(a5)                                             // Word load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_5, test_5_str)

    \TEST_CASE\()_6:
    lwu a4, 0(a5)                                            // Word load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_6, test_6_str)


    LI(a4, NOP64)

    \TEST_CASE\()_7:
    sd a4, 0(a5)                                             // Doubleword-level store test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_7, test_7_str)

    \TEST_CASE\()_8:
    ld a4, 0(a5)                                             // Doubleword load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_8, test_8_str)


    LI(a4, NOP32)

    // Access Check straddling end
    LA(a5, (\ADDRESS+g-1))

    \TEST_CASE\()_9:
    sh a4, 0(a5)                                             // Half-word store test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_9, test_9_str)

    \TEST_CASE\()_10:
    lh a4, 0(a5)                                             // Half-word load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_10, test_10_str)

    \TEST_CASE\()_11:
    lhu a4, 0(a5)                                            // Half-word load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_11, test_11_str)


    LI(a4, NOP32)

    \TEST_CASE\()_12:
    sw a4, 0(a5)                                             // Word-level store test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_12, test_12_str)

    \TEST_CASE\()_13:
    lw a4, 0(a5)                                             // Word load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_13, test_13_str)

    \TEST_CASE\()_14:
    lwu a4, 0(a5)                                            // Word load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_14, test_14_str)


    LI(a4, NOP64)

    \TEST_CASE\()_15:
    sd a4, 0(a5)                                             // Doubleword-level store test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_15, test_15_str)

    \TEST_CASE\()_16:
    ld a4, 0(a5)                                             // Doubleword load test
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4, \TEST_CASE\()_16, test_16_str)

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
#define PMPREGION_LXWR      ((((PMP_L|PMP_R|PMP_W|PMP_X)          &0xFF) << PMP0_CFG_SHIFT))
#define PMPREGION_XWR       ((((      PMP_R|PMP_W|PMP_X)          &0xFF) << PMP0_CFG_SHIFT))

#define PMPADDRESS_TOP_GLOBAL        -1                                                // All memory region
#define REGIONSTART        0x80002000        // RAM_BASE_ADDR + PROGRAM_SIZE
#define OFF_REGION         (REGIONSTART >> PMP_SHIFT)


    LA(x4, PMPADDRESS_TOP_GLOBAL)
    csrw     pmpaddr15, x4

    //Lock the Background region.
    LI(x4, PMP_REGION_GLOBAL)
    csrw pmpcfg2, x4

    LA(x4, OFF_REGION)
    csrw     pmpaddr0, x4

//                                            Verification Section
// Test Case: 1 -- XWR Permissions given to the PMP Region.

    LI(x4, PMPREGION_XWR)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION,test_1

// Test Case: 2 -- LXWR Permissions given to the PMP Region.

    LI(x4, PMPREGION_LXWR)
    csrw pmpcfg0, x4

    VERIFICATION_RWX    TEST_FOR_EXECUTION,test_2

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
test_1_str:  .string "\"test: 1;  cp: pmpm_misaligned_napot_sh_address-1\""
test_2_str:  .string "\"test: 2;  cp: pmpm_misaligned_napot_lh_address-1\""
test_3_str:  .string "\"test: 3;  cp: pmpm_misaligned_napot_lhu_address-1\""
test_4_str:  .string "\"test: 4;  cp: pmpm_misaligned_napot_sw_address-1\""
test_5_str:  .string "\"test: 5;  cp: pmpm_misaligned_napot_lw_address-1\""
test_6_str:  .string "\"test: 6;  cp: pmpm_misaligned_napot_lwu_address-1\""
test_7_str:  .string "\"test: 7;  cp: pmpm_misaligned_napot_sd_address-1\""
test_8_str:  .string "\"test: 8;  cp: pmpm_misaligned_napot_ld_address-1\""

test_9_str:  .string "\"test: 9;  cp: pmpm_misaligned_napot_sh_address+g-1\""
test_10_str: .string "\"test: 10; cp: pmpm_misaligned_napot_lh_address+g-1\""
test_11_str: .string "\"test: 11; cp: pmpm_misaligned_napot_lhu_address+g-1\""
test_12_str: .string "\"test: 12; cp: pmpm_misaligned_napot_sw_address+g-1\""
test_13_str: .string "\"test: 13; cp: pmpm_misaligned_napot_lw_address+g-1\""
test_14_str: .string "\"test: 14; cp: pmpm_misaligned_napot_lwu_address+g-1\""
test_15_str: .string "\"test: 15; cp: pmpm_misaligned_napot_sd_address+g-1\""
test_16_str: .string "\"test: 16; cp: pmpm_misaligned_napot_ld_address+g-1\""

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
