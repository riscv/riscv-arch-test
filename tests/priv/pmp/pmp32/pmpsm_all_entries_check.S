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
// Coverpoints : cp_pmp64 for PMPSM is completely covered in this test file.
//
// Test Cases  : Checking all (64-PMP_writable_regs) PMP registers affect load/store
//               access. Just basic checks since bottom PMP_writable_regs have been
//               tested thoroughly. 64 Regions Only, With pmpcfg.L=1, pmpcfg.XWR=101,
//               attempt to lw and sw to each standard region. Read should succeed and
//               write should fail, proving all PMP entries are usable.
//
// --------------------------------------------------------------------------------

##### START_TEST_CONFIG #####
# REQUIRED_EXTENSIONS: ['I','Smpmp']
# params:
#   MXLEN: 32
# MARCH: rv32i_zicsr
# CONFIG_DEPENDENT: true
##### END_TEST_CONFIG #####

// Define the name of this test file for reporting and the size of the signature region
#define TEST_FILE "pmpsm_all_entries_check-01.S"
#define SIGUPD_COUNT 50

// Enable trap handler
#define rvtest_mtrap_routine
#define RVTEST_PRIV_TEST

#define SKIP_MEPC

// Include framework macros
#include "riscv_arch_test.h"

// Set up test environment and declare main entry point
RVTEST_BEGIN

#define NOP         0x13

.macro VERIFICATION_RWX ADDRESS, TEST_CASE

    LA(a5, \ADDRESS)                                        // Address to be ve
    \TEST_CASE\()_1:
    sw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4,\TEST_CASE\()_1,test_1_str)
    \TEST_CASE\()_2:
    lw a4, 0(a5)
    nop
    RVTEST_SIGUPD(x2, x5, x4, a4,\TEST_CASE\()_2,test_2_str)

.endm

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

#define PMP_REGION_GLOBAL   ((PMP_L|PMP_R|PMP_W|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT // Background region with RWX enable.
#define PMP_REGION_62       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT
#define PMP_REGION_61       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT
#define PMP_REGION_60       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT
#define PMP_REGION_59       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT
#define PMP_REGION_58       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT
#define PMP_REGION_57       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT
#define PMP_REGION_56       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT
#define PMP_REGION_55       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT
#define PMP_REGION_54       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT
#define PMP_REGION_53       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT
#define PMP_REGION_52       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT
#define PMP_REGION_51       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT
#define PMP_REGION_50       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT
#define PMP_REGION_49       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT
#define PMP_REGION_48       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT
#define PMP_REGION_47       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT
#define PMP_REGION_46       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT
#define PMP_REGION_45       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT
#define PMP_REGION_44       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT
#define PMP_REGION_43       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT
#define PMP_REGION_42       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT
#define PMP_REGION_41       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT
#define PMP_REGION_40       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT
#define PMP_REGION_39       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT
#define PMP_REGION_38       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT
#define PMP_REGION_37       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT
#define PMP_REGION_36       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT
#define PMP_REGION_35       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT
#define PMP_REGION_34       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT
#define PMP_REGION_33       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT
#define PMP_REGION_32       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT
#define PMP_REGION_31       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT
#define PMP_REGION_30       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT
#define PMP_REGION_29       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT
#define PMP_REGION_28       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT
#define PMP_REGION_27       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT
#define PMP_REGION_26       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT
#define PMP_REGION_25       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT
#define PMP_REGION_24       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT
#define PMP_REGION_23       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT
#define PMP_REGION_22       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT
#define PMP_REGION_21       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT
#define PMP_REGION_20       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT
#define PMP_REGION_19       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP3_CFG_SHIFT
#define PMP_REGION_18       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP2_CFG_SHIFT
#define PMP_REGION_17       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP1_CFG_SHIFT
#define PMP_REGION_16       ((PMP_L|PMP_R|PMP_X|PMP_NAPOT)&0xFF) << PMP0_CFG_SHIFT

#define PMPADDRESS_TOP_GLOBAL       -1                                              // All memory region
#define REGIONSTART         0x80002000      // RAM_BASE_ADDR + PROGRAM_SIZE
#define PMP_MASK            ~((1 << (RVMODEL_PMP_GRAIN - 1))-1)
#define PMP_REGION_SIZE     ((1 << (RVMODEL_PMP_GRAIN - 1))-1)

#if RVMODEL_PMP_GRAIN != 0
    #define STANDARD_REGION   (((REGIONSTART >> PMP_SHIFT) & PMP_MASK) | PMP_REGION_SIZE)
#else
    #define STANDARD_REGION   (REGIONSTART >> PMP_SHIFT)
#endif

    LA(x4, PMPADDRESS_TOP_GLOBAL)
    csrw    pmpaddr63, x4

    //Lock the Background region.
    LI(x4, (PMP_REGION_GLOBAL))
    csrw pmpcfg15, x4

//                                          Verification Section
// Test Case: 1 : L -> 1 and XR Permissions given to the PMP Region 62
    LI(x5, STANDARD_REGION)
    csrw pmpaddr62, x5
    LI(x4, PMP_REGION_62)
    csrw pmpcfg15, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_1


// Test Case: 2 : L -> 1 and XR Permissions given to the PMP Region 61
    LI(x5, STANDARD_REGION)
    csrw pmpaddr61, x5
    LI(x4, PMP_REGION_61)
    csrw pmpcfg15, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_2


// Test Case: 3 : L -> 1 and XR Permissions given to the PMP Region 60
    LI(x5, STANDARD_REGION)
    csrw pmpaddr60, x5
    LI(x4, PMP_REGION_60)
    csrw pmpcfg15, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_3


// Test Case: 4 : PMP Region 59
    LI(x5, STANDARD_REGION)
    csrw pmpaddr59, x5
    LI(x4, PMP_REGION_59)
    csrw pmpcfg14, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_4


// Test Case: 5 : PMP Region 58
    LI(x5, STANDARD_REGION)
    csrw pmpaddr58, x5
    LI(x4, PMP_REGION_58)
    csrw pmpcfg14, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_5


// Test Case: 6 : PMP Region 57
    LI(x5, STANDARD_REGION)
    csrw pmpaddr57, x5
    LI(x4, PMP_REGION_57)
    csrw pmpcfg14, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_6


// Test Case: 7 : PMP Region 56
    LI(x5, STANDARD_REGION)
    csrw pmpaddr56, x5
    LI(x4, PMP_REGION_56)
    csrw pmpcfg14, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_7


// Test Case: 8 : PMP Region 55
    LI(x5, STANDARD_REGION)
    csrw pmpaddr55, x5
    LI(x4, PMP_REGION_55)
    csrw pmpcfg13, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_8


// Test Case: 9 : PMP Region 54
    LI(x5, STANDARD_REGION)
    csrw pmpaddr54, x5
    LI(x4, PMP_REGION_54)
    csrw pmpcfg13, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_9


// Test Case: 10 : PMP Region 53
    LI(x5, STANDARD_REGION)
    csrw pmpaddr53, x5
    LI(x4, PMP_REGION_53)
    csrw pmpcfg13, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_10


// Test Case: 11 : PMP Region 52
    LI(x5, STANDARD_REGION)
    csrw pmpaddr52, x5
    LI(x4, PMP_REGION_52)
    csrw pmpcfg13, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_11


// Test Case: 12 : PMP Region 51
    LI(x5, STANDARD_REGION)
    csrw pmpaddr51, x5
    LI(x4, PMP_REGION_51)
    csrw pmpcfg12, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_12


// Test Case: 13 : PMP Region 50
    LI(x5, STANDARD_REGION)
    csrw pmpaddr50, x5
    LI(x4, PMP_REGION_50)
    csrw pmpcfg12, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_13


// Test Case: 14 : PMP Region 49
    LI(x5, STANDARD_REGION)
    csrw pmpaddr49, x5
    LI(x4, PMP_REGION_49)
    csrw pmpcfg12, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_14


// Test Case: 15 : PMP Region 48
    LI(x5, STANDARD_REGION)
    csrw pmpaddr48, x5
    LI(x4, PMP_REGION_48)
    csrw pmpcfg12, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_15


// Test Case: 16 : PMP Region 47
    LI(x5, STANDARD_REGION)
    csrw pmpaddr47, x5
    LI(x4, PMP_REGION_47)
    csrw pmpcfg11, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_16


// Test Case: 17 : PMP Region 46
    LI(x5, STANDARD_REGION)
    csrw pmpaddr46, x5
    LI(x4, PMP_REGION_46)
    csrw pmpcfg11, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_17


// Test Case: 18 : PMP Region 45
    LI(x5, STANDARD_REGION)
    csrw pmpaddr45, x5
    LI(x4, PMP_REGION_45)
    csrw pmpcfg11, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_18


// Test Case: 19 : PMP Region 44
    LI(x5, STANDARD_REGION)
    csrw pmpaddr44, x5
    LI(x4, PMP_REGION_44)
    csrw pmpcfg11, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_19


// Test Case: 20 : PMP Region 43
    LI(x5, STANDARD_REGION)
    csrw pmpaddr43, x5
    LI(x4, PMP_REGION_43)
    csrw pmpcfg10, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_20


// Test Case: 21 : PMP Region 42
    LI(x5, STANDARD_REGION)
    csrw pmpaddr42, x5
    LI(x4, PMP_REGION_42)
    csrw pmpcfg10, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_21


// Test Case: 22 : PMP Region 41
    LI(x5, STANDARD_REGION)
    csrw pmpaddr41, x5
    LI(x4, PMP_REGION_41)
    csrw pmpcfg10, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_22


// Test Case: 23 : PMP Region 40
    LI(x5, STANDARD_REGION)
    csrw pmpaddr40, x5
    LI(x4, PMP_REGION_40)
    csrw pmpcfg10, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_23


// Test Case: 24 : PMP Region 39
    LI(x5, STANDARD_REGION)
    csrw pmpaddr39, x5
    LI(x4, PMP_REGION_39)
    csrw pmpcfg9, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_24


// Test Case: 25 : PMP Region 38
    LI(x5, STANDARD_REGION)
    csrw pmpaddr38, x5
    LI(x4, PMP_REGION_38)
    csrw pmpcfg9, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_25


// Test Case: 26 : PMP Region 37
    LI(x5, STANDARD_REGION)
    csrw pmpaddr37, x5
    LI(x4, PMP_REGION_37)
    csrw pmpcfg9, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_26


// Test Case: 27 : PMP Region 36
    LI(x5, STANDARD_REGION)
    csrw pmpaddr36, x5
    LI(x4, PMP_REGION_36)
    csrw pmpcfg9, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_27


// Test Case: 28 : PMP Region 35
    LI(x5, STANDARD_REGION)
    csrw pmpaddr35, x5
    LI(x4, PMP_REGION_35)
    csrw pmpcfg8, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_28


// Test Case: 29 : PMP Region 34
    LI(x5, STANDARD_REGION)
    csrw pmpaddr34, x5
    LI(x4, PMP_REGION_34)
    csrw pmpcfg8, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_29


// Test Case: 30 : PMP Region 33
    LI(x5, STANDARD_REGION)
    csrw pmpaddr33, x5
    LI(x4, PMP_REGION_33)
    csrw pmpcfg8, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_30


// Test Case: 31 : PMP Region 32
    LI(x5, STANDARD_REGION)
    csrw pmpaddr32, x5
    LI(x4, PMP_REGION_32)
    csrw pmpcfg8, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_31


// Test Case: 32 : PMP Region 31
    LI(x5, STANDARD_REGION)
    csrw pmpaddr31, x5
    LI(x4, PMP_REGION_31)
    csrw pmpcfg7, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_32


// Test Case: 33 : PMP Region 30
    LI(x5, STANDARD_REGION)
    csrw pmpaddr30, x5
    LI(x4, PMP_REGION_30)
    csrw pmpcfg7, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_33


// Test Case: 34 : PMP Region 29
    LI(x5, STANDARD_REGION)
    csrw pmpaddr29, x5
    LI(x4, PMP_REGION_29)
    csrw pmpcfg7, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_34


// Test Case: 35 : PMP Region 28
    LI(x5, STANDARD_REGION)
    csrw pmpaddr28, x5
    LI(x4, PMP_REGION_28)
    csrw pmpcfg7, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_35


// Test Case: 36 : PMP Region 27
    LI(x5, STANDARD_REGION)
    csrw pmpaddr27, x5
    LI(x4, PMP_REGION_27)
    csrw pmpcfg6, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_36


// Test Case: 37 : PMP Region 26
    LI(x5, STANDARD_REGION)
    csrw pmpaddr26, x5
    LI(x4, PMP_REGION_26)
    csrw pmpcfg6, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_37


// Test Case: 38 : PMP Region 25
    LI(x5, STANDARD_REGION)
    csrw pmpaddr25, x5
    LI(x4, PMP_REGION_25)
    csrw pmpcfg6, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_38


// Test Case: 39 : PMP Region 24
    LI(x5, STANDARD_REGION)
    csrw pmpaddr24, x5
    LI(x4, PMP_REGION_24)
    csrw pmpcfg6, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_39


// Test Case: 40 : PMP Region 23
    LI(x5, STANDARD_REGION)
    csrw pmpaddr23, x5
    LI(x4, PMP_REGION_23)
    csrw pmpcfg5, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_40


// Test Case: 41 : PMP Region 22
    LI(x5, STANDARD_REGION)
    csrw pmpaddr22, x5
    LI(x4, PMP_REGION_22)
    csrw pmpcfg5, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_41


// Test Case: 42 : PMP Region 21
    LI(x5, STANDARD_REGION)
    csrw pmpaddr21, x5
    LI(x4, PMP_REGION_21)
    csrw pmpcfg5, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_42


// Test Case: 43 : PMP Region 20
    LI(x5, STANDARD_REGION)
    csrw pmpaddr20, x5
    LI(x4, PMP_REGION_20)
    csrw pmpcfg5, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_43


// Test Case: 44 : PMP Region 19
    LI(x5, STANDARD_REGION)
    csrw pmpaddr19, x5
    LI(x4, PMP_REGION_19)
    csrw pmpcfg4, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_44


// Test Case: 45 : PMP Region 18
    LI(x5, STANDARD_REGION)
    csrw pmpaddr18, x5
    LI(x4, PMP_REGION_18)
    csrw pmpcfg4, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_45


// Test Case: 46 : PMP Region 17
    LI(x5, STANDARD_REGION)
    csrw pmpaddr17, x5
    LI(x4, PMP_REGION_17)
    csrw pmpcfg4, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_46


// Test Case: 47 : PMP Region 16
    LI(x5, STANDARD_REGION)
    csrw pmpaddr16, x5
    LI(x4, PMP_REGION_16)
    csrw pmpcfg4, x4
    VERIFICATION_RWX    TEST_FOR_EXECUTION, test_47

    j exit                                                      // Verification Complete, exit the test

.align 13
.align (RVMODEL_PMP_GRAIN+2)
TEST_FOR_EXECUTION:
    .rept (1<<(RVMODEL_PMP_GRAIN+2))
    nop
    .endr

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
test_1_str: .string "\"test: 1; cp: cp_pmpm64_sw\""
test_2_str: .string "\"test: 2; cp: cp_pmpm64_lw\""

RVTEST_DATA_END

// Signature region for self-checking
RVTEST_SIG_SETUP
